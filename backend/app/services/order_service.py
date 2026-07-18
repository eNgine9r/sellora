from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.inventory_transaction import InventoryTransactionType
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.product_variant import ProductVariant
from app.repositories.advertising_repository import AdCampaignRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.inventory import InventoryTransactionCreate
from app.schemas.order import OrderCreate, OrderDashboardResponse, OrderStatusUpdate, OrderUpdate
from app.services.business_utils import snapshot
from app.services.inventory_service import InventoryService, InventoryServiceError


class OrderServiceError(ValueError):
    pass


class OrderService:
    allowed_status_transitions = {
        OrderStatus.NEW: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
        OrderStatus.CONFIRMED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
        OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.RETURNED},
        OrderStatus.DELIVERED: {OrderStatus.COMPLETED, OrderStatus.RETURNED},
        OrderStatus.COMPLETED: {OrderStatus.RETURNED},
        OrderStatus.RETURNED: set(),
        OrderStatus.CANCELLED: set(),
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.inventory = InventoryRepository(db)
        self.inventory_service = InventoryService(db)
        self.audit_logs = AuditLogRepository(db)
        self.campaigns = AdCampaignRepository(db)

    def list(self, workspace_id: UUID, status: OrderStatus | None = None) -> list[Order]:
        return self.orders.list_for_workspace(workspace_id, status.value if status else None)

    def get(self, workspace_id: UUID, order_id: UUID) -> Order | None:
        return self.orders.get(workspace_id, order_id)

    def _get_order_for_update(self, workspace_id: UUID, order_id: UUID) -> Order | None:
        getter = getattr(self.orders, "get_for_update", None)
        return getter(workspace_id, order_id) if getter else self.orders.get(workspace_id, order_id)

    def dashboard_today(self, workspace_id: UUID) -> OrderDashboardResponse:
        orders_today, revenue_today, profit_today = self.orders.dashboard_today(workspace_id)
        return OrderDashboardResponse(orders_today=orders_today, revenue_today=revenue_today, profit_today=profit_today)

    def create(self, workspace_id: UUID, payload: OrderCreate, actor_user_id: UUID | None, affect_inventory: bool = True, order_number: str | None = None, created_at: datetime | None = None, completed_at: datetime | None = None, *, commit: bool = True) -> Order:
        customer = self._get_order_customer(workspace_id, payload.customer_id, payload.is_historical)
        self._validate_campaign(workspace_id, payload.campaign_id)
        prepared_items = []
        requested_by_inventory: dict[UUID, int] = {}
        inventory_by_variant = {}
        if affect_inventory:
            variant_ids = sorted({item.product_variant_id for item in payload.items}, key=str)
            inventory_rows = self.inventory.list_by_variants_for_update(workspace_id, variant_ids) if hasattr(self.inventory, "list_by_variants_for_update") else [self.inventory.get_by_variant(workspace_id, variant_id) for variant_id in variant_ids]
            inventory_by_variant = {row.product_variant_id: row for row in inventory_rows if row is not None}
        for item_payload in payload.items:
            variant = self._get_variant(workspace_id, item_payload.product_variant_id)
            inventory = inventory_by_variant.get(item_payload.product_variant_id) if affect_inventory else None
            if affect_inventory:
                if inventory is None:
                    raise OrderServiceError("Inventory record not found for variant")
                requested_by_inventory[inventory.id] = requested_by_inventory.get(inventory.id, 0) + item_payload.quantity
                if requested_by_inventory[inventory.id] > inventory.stock_quantity - inventory.reserved_quantity:
                    raise OrderServiceError("Cannot reserve more than available stock")
            prepared_items.append((item_payload, variant, inventory))

        initial_status = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
        order = self.orders.create(
            Order(
                workspace_id=workspace_id,
                order_number=order_number or self._generate_order_number(workspace_id),
                customer_id=customer.id if customer else None,
                campaign_id=payload.campaign_id,
                status=initial_status,
                payment_status=payload.payment_status.value,
                is_historical=payload.is_historical,
                ad_cost=payload.ad_cost,
                shipping_cost=payload.shipping_cost,
                cod_fee=payload.cod_fee,
                other_cost=payload.other_cost,
                notes=payload.notes,
                completed_at=completed_at,
            )
        )
        if created_at is not None:
            order.created_at = created_at
        revenue = Decimal("0")
        product_cost = Decimal("0")
        for item_payload, variant, inventory in prepared_items:
            line_total = item_payload.unit_price * item_payload.quantity
            line_cost = item_payload.unit_cost * item_payload.quantity
            revenue += line_total
            product_cost += line_cost
            self.orders.add_item(
                OrderItem(
                    workspace_id=workspace_id,
                    order_id=order.id,
                    product_variant_id=variant.id,
                    sku=variant.sku,
                    product_name=variant.product.name,
                    quantity=item_payload.quantity,
                    unit_price=item_payload.unit_price,
                    unit_cost=item_payload.unit_cost,
                    line_total=line_total,
                    line_cost=line_cost,
                )
            )
            if affect_inventory and inventory is not None:
                self._inventory_transaction(workspace_id, inventory.id, InventoryTransactionType.RESERVE, item_payload.quantity, "Order reservation", actor_user_id)
        order.revenue = revenue
        order.product_cost = product_cost
        self._recalculate_profit(order)
        self._add_status_history(order, None, OrderStatus(initial_status), actor_user_id, "Order created")
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Order", entity_id=order.id, action="CREATE", new_value=snapshot(order))
        if commit:
            self.db.commit()
            self.db.refresh(order)
        else:
            self.db.flush()
        return order

    def update(self, workspace_id: UUID, order_id: UUID, payload: OrderUpdate, actor_user_id: UUID | None) -> Order | None:
        order = self._get_order_for_update(workspace_id, order_id)
        if order is None:
            return None
        old_value = snapshot(order)
        if "customer_id" in payload.model_fields_set:
            if payload.customer_id is None:
                raise OrderServiceError("Customer is required to update an order")
            customer = self._get_order_customer(workspace_id, payload.customer_id, is_historical=False)
            order.customer_id = customer.id
            order.customer = customer
        item_payloads = payload.items if "items" in payload.model_fields_set else None
        if "campaign_id" in payload.model_fields_set:
            self._validate_campaign(workspace_id, payload.campaign_id)
        changes = payload.model_dump(exclude_unset=True, exclude={"items", "customer_id"})
        for field, value in changes.items():
            setattr(order, field, value.value if hasattr(value, "value") else value)
        if item_payloads is not None:
            self._replace_items_for_update(workspace_id, order, item_payloads, actor_user_id, old_value)
        self._recalculate_profit(order)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Order", entity_id=order.id, action="ORDER_UPDATE", old_value=old_value, new_value=snapshot(order))
        self.db.commit()
        self.db.refresh(order)
        return self.get(workspace_id, order_id) or order

    def _replace_items_for_update(self, workspace_id: UUID, order: Order, item_payloads: list, actor_user_id: UUID | None, old_value: dict | None = None) -> None:
        if OrderStatus(order.status) not in {OrderStatus.NEW, OrderStatus.CONFIRMED}:
            raise OrderServiceError("Order items cannot be edited after shipment workflow has started")
        prepared_items = []
        old_quantities: dict[UUID, int] = {}
        new_quantities: dict[UUID, int] = {}
        inventories = {}
        for item in order.items:
            old_quantities[item.product_variant_id] = old_quantities.get(item.product_variant_id, 0) + item.quantity
        for item_payload in item_payloads:
            variant = self._get_variant(workspace_id, item_payload.product_variant_id)
            inventory = self.inventory.get_by_variant(workspace_id, item_payload.product_variant_id)
            if inventory is None:
                raise OrderServiceError("Inventory record not found for variant")
            prepared_items.append((item_payload, variant, inventory))
            inventories[item_payload.product_variant_id] = inventory
            new_quantities[item_payload.product_variant_id] = new_quantities.get(item_payload.product_variant_id, 0) + item_payload.quantity
        for variant_id in set(old_quantities) | set(new_quantities):
            inventory = inventories.get(variant_id) or self.inventory.get_by_variant(workspace_id, variant_id)
            if inventory is None:
                raise OrderServiceError("Inventory record not found for order item")
            delta = new_quantities.get(variant_id, 0) - old_quantities.get(variant_id, 0)
            if delta > 0 and delta > inventory.stock_quantity - inventory.reserved_quantity:
                raise OrderServiceError("Not enough available stock for one or more items")
            if delta < 0 and abs(delta) > inventory.reserved_quantity:
                raise OrderServiceError("Inventory changed. Please refresh and try again")
        for variant_id in sorted(set(old_quantities) | set(new_quantities), key=str):
            inventory = inventories.get(variant_id) or self.inventory.get_by_variant(workspace_id, variant_id)
            delta = new_quantities.get(variant_id, 0) - old_quantities.get(variant_id, 0)
            if delta > 0:
                self._inventory_transaction(workspace_id, inventory.id, InventoryTransactionType.RESERVE, delta, "Order item edit reservation", actor_user_id)
            elif delta < 0:
                self._inventory_transaction(workspace_id, inventory.id, InventoryTransactionType.UNRESERVE, abs(delta), "Order item edit release reservation", actor_user_id)
        for item in list(order.items):
            self.orders.delete_item(item)
        order.items = []
        revenue = Decimal("0")
        product_cost = Decimal("0")
        for item_payload, variant, _inventory in prepared_items:
            line_total = item_payload.unit_price * item_payload.quantity
            line_cost = item_payload.unit_cost * item_payload.quantity
            revenue += line_total
            product_cost += line_cost
            self.orders.add_item(
                OrderItem(
                    workspace_id=workspace_id,
                    order_id=order.id,
                    product_variant_id=variant.id,
                    sku=variant.sku,
                    product_name=variant.product.name,
                    quantity=item_payload.quantity,
                    unit_price=item_payload.unit_price,
                    unit_cost=item_payload.unit_cost,
                    line_total=line_total,
                    line_cost=line_cost,
                )
            )
        order.revenue = revenue
        order.product_cost = product_cost
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Order", entity_id=order.id, action="ORDER_ITEMS_UPDATE", old_value=old_value, new_value={"item_count": len(prepared_items)})

    def delete(self, workspace_id: UUID, order_id: UUID, actor_user_id: UUID | None) -> bool:
        order = self._get_order_for_update(workspace_id, order_id)
        if order is None:
            return False
        current_status = OrderStatus(order.status)
        if current_status not in {OrderStatus.NEW, OrderStatus.CANCELLED}:
            raise OrderServiceError("This order cannot be archived in its current status. Cancel or return it through the status workflow first.")
        old_value = snapshot(order)
        if current_status == OrderStatus.NEW:
            for item in order.items:
                inventory = self.inventory.get_by_variant(workspace_id, item.product_variant_id)
                if inventory is None:
                    raise OrderServiceError("Inventory record not found for order item")
                if inventory.reserved_quantity < item.quantity:
                    raise OrderServiceError("This order cannot be archived because reserved inventory is inconsistent")
                self._inventory_transaction(workspace_id, inventory.id, InventoryTransactionType.UNRESERVE, item.quantity, "Order archived", actor_user_id)
        self.orders.soft_delete(order, actor_user_id)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Order", entity_id=order.id, action="ORDER_ARCHIVE", old_value=old_value, new_value=snapshot(order))
        self.db.commit()
        return True

    def change_status(self, workspace_id: UUID, order_id: UUID, payload: OrderStatusUpdate, actor_user_id: UUID | None, commit: bool = True) -> Order | None:
        order = self._get_order_for_update(workspace_id, order_id)
        if order is None:
            return None
        new_status = payload.status
        old_status = OrderStatus(order.status)
        if old_status == new_status:
            return order
        if new_status not in self.allowed_status_transitions.get(old_status, set()):
            raise OrderServiceError(f"Order status transition {old_status.value} -> {new_status.value} is not allowed")
        self._apply_transition_inventory(workspace_id, order, old_status, new_status, actor_user_id)
        old_value = snapshot(order)
        order.status = new_status.value
        if new_status == OrderStatus.COMPLETED:
            order.completed_at = datetime.now(UTC)
            self._update_customer_metrics(workspace_id, order)
        self._add_status_history(order, old_status, new_status, actor_user_id, payload.note)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Order", entity_id=order.id, action=f"STATUS_{new_status.value}", old_value=old_value, new_value=snapshot(order))
        if commit:
            self.db.commit()
            self.db.refresh(order)
        else:
            flush = getattr(self.db, "flush", None)
            if flush:
                flush()
        return order

    def _apply_transition_inventory(self, workspace_id: UUID, order: Order, old_status: OrderStatus, new_status: OrderStatus, actor_user_id: UUID | None) -> None:
        for item in sorted(order.items, key=lambda value: str(value.product_variant_id)):
            inventory = self.inventory.get_by_variant(workspace_id, item.product_variant_id)
            if inventory is None:
                raise OrderServiceError("Inventory record not found for order item")
            if new_status == OrderStatus.SHIPPED and old_status not in {OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.COMPLETED}:
                self._inventory_transaction(workspace_id, inventory.id, InventoryTransactionType.UNRESERVE, item.quantity, "Order shipped release reservation", actor_user_id)
                self._inventory_transaction(workspace_id, inventory.id, InventoryTransactionType.STOCK_OUT, item.quantity, "Order shipped stock out", actor_user_id)
            elif new_status == OrderStatus.CANCELLED and old_status in {OrderStatus.NEW, OrderStatus.CONFIRMED}:
                self._inventory_transaction(workspace_id, inventory.id, InventoryTransactionType.UNRESERVE, item.quantity, "Order cancelled", actor_user_id)
            elif new_status == OrderStatus.RETURNED and old_status in {OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.COMPLETED}:
                self._inventory_transaction(workspace_id, inventory.id, InventoryTransactionType.RETURN, item.quantity, "Order returned", actor_user_id)

    def _inventory_transaction(self, workspace_id: UUID, inventory_id: UUID, transaction_type: InventoryTransactionType, quantity: int, reason: str, actor_user_id: UUID | None) -> None:
        try:
            self.inventory_service.record_transaction(workspace_id, inventory_id, InventoryTransactionCreate(transaction_type=transaction_type, quantity=quantity, reason=reason), actor_user_id, commit=False)
        except InventoryServiceError as exc:
            raise OrderServiceError(str(exc)) from exc

    def _generate_order_number(self, workspace_id: UUID) -> str:
        year = datetime.now(UTC).year
        sequence = self.orders.next_sequence_for_year(workspace_id, year)
        return f"ORD-{year}-{sequence:06d}"

    def _get_variant(self, workspace_id: UUID, variant_id: UUID) -> ProductVariant:
        variant = self.db.get(ProductVariant, variant_id)
        if variant is None or variant.workspace_id != workspace_id or variant.deleted_at is not None:
            raise OrderServiceError("Product variant does not exist in this workspace")
        if variant.is_active is False or (variant.product is not None and variant.product.is_active is False):
            raise OrderServiceError("Product variant is archived and cannot be used in new orders")
        return variant

    def _get_order_customer(self, workspace_id: UUID, customer_id: UUID | None, is_historical: bool) -> Customer | None:
        if customer_id is None:
            if is_historical:
                return None
            raise OrderServiceError("Customer is required to create an order")
        customer = self.db.get(Customer, customer_id)
        if customer is None or customer.workspace_id != workspace_id or customer.deleted_at is not None:
            raise OrderServiceError("Customer not found in this workspace")
        return customer

    def _recalculate_profit(self, order: Order) -> None:
        order.net_profit = order.revenue - order.product_cost - order.ad_cost - order.shipping_cost - order.cod_fee - order.other_cost

    def _add_status_history(self, order: Order, from_status: OrderStatus | None, to_status: OrderStatus, actor_user_id: UUID | None, note: str | None) -> None:
        self.orders.add_status_history(OrderStatusHistory(workspace_id=order.workspace_id, order_id=order.id, from_status=from_status.value if from_status else None, to_status=to_status.value, changed_by=actor_user_id, note=note))

    def _update_customer_metrics(self, workspace_id: UUID, order: Order) -> None:
        if order.customer_id is None:
            return
        customer = self.db.get(Customer, order.customer_id)
        if customer is None or customer.workspace_id != workspace_id:
            return
        customer.total_orders += 1
        customer.total_spent += order.revenue
        customer.last_order_at = datetime.now(UTC)

    def _validate_campaign(self, workspace_id: UUID, campaign_id: UUID | None) -> None:
        if campaign_id and self.campaigns.get(workspace_id, campaign_id) is None:
            raise OrderServiceError("Campaign does not exist in this workspace")
