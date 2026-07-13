from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction, InventoryTransactionType
from app.models.lead import Lead, LeadStatus
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.role import RoleName
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_user import WorkspaceUser
from app.repositories.audit_log_repository import AuditLogRepository, DEMO_WORKSPACE_CREATE_ACTION
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceSettingsUpdate, WorkspaceUserCreate
from app.services.business_utils import snapshot

DUPLICATE_USER_MESSAGE = "Користувач уже доданий до команди."
LAST_OWNER_ROLE_MESSAGE = "Неможливо змінити роль останнього власника робочого простору."
LAST_OWNER_DEACTIVATE_MESSAGE = "Неможливо деактивувати останнього власника робочого простору."
DEMO_WORKSPACE_NAME = "Демо Sellora"
DEMO_WORKSPACE_SLUG_PREFIX = "demo-sellora"


class WorkspaceValidationError(ValueError):
    pass


class WorkspacePermissionError(PermissionError):
    pass


class WorkspaceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit_logs = AuditLogRepository(db)
        self.workspaces = WorkspaceRepository(db)
        self.users = UserRepository(db)

    def list_available_workspaces(self, user_id: UUID) -> list[WorkspaceUser]:
        return self.workspaces.list_for_user(user_id)

    def create_workspace(self, payload: WorkspaceCreate, actor_user_id: UUID) -> WorkspaceUser:
        if self.workspaces.get_by_slug(payload.slug):
            raise WorkspaceValidationError("Workspace slug already exists")
        try:
            workspace = self.workspaces.create_workspace(name=payload.name.strip(), slug=payload.slug, currency_code=payload.currency_code.value, timezone=payload.timezone)
            membership = self.workspaces.add_membership(workspace_id=workspace.id, user_id=actor_user_id, role=RoleName.OWNER)
            self.db.commit()
            return membership
        except Exception:
            self.db.rollback()
            raise

    def _find_actor_demo_workspace(self, actor_user_id: UUID) -> WorkspaceUser | None:
        for membership in self.workspaces.list_for_user(actor_user_id):
            if self.audit_logs.has_demo_workspace_provenance(membership.workspace_id, creator_user_id=actor_user_id):
                return membership
        return None

    def _assert_demo_creation_access(self, actor_user_id: UUID) -> None:
        memberships = self.workspaces.list_for_user(actor_user_id)
        if memberships and not any(membership.role.name == RoleName.OWNER.value for membership in memberships):
            raise WorkspacePermissionError("Only workspace owners can create or manage a demo workspace")

    def create_or_get_demo_workspace(self, actor_user_id: UUID, *, locale: str = "uk", currency_code: str = "UAH") -> WorkspaceUser:
        existing = self._find_actor_demo_workspace(actor_user_id)
        if existing is not None:
            return existing
        self._assert_demo_creation_access(actor_user_id)

        slug = f"{DEMO_WORKSPACE_SLUG_PREFIX}-{str(actor_user_id).split('-')[0]}"
        if self.workspaces.get_by_slug(slug):
            slug = f"{slug}-{uuid4().hex[:6]}"
        try:
            workspace = self.workspaces.create_workspace(name=DEMO_WORKSPACE_NAME, slug=slug, currency_code=currency_code, timezone="Europe/Kyiv")
            membership = self.workspaces.add_membership(workspace_id=workspace.id, user_id=actor_user_id, role=RoleName.OWNER)
            self._seed_demo_dataset(workspace.id, actor_user_id)
            self.db.commit()
            self.db.refresh(membership)
            return membership
        except IntegrityError:
            # A concurrent duplicate request may lose the deterministic slug race.
            # Roll back the failed transaction and return the demo committed by
            # the winning request instead of creating a second workspace.
            self.db.rollback()
            existing = self._find_actor_demo_workspace(actor_user_id)
            if existing is not None:
                return existing
            raise
        except Exception:
            self.db.rollback()
            raise

    def deactivate_demo_workspace(self, workspace_id: UUID, actor_user_id: UUID) -> WorkspaceUser:
        membership = self.require_owner(workspace_id, actor_user_id)
        if not self.audit_logs.has_demo_workspace_provenance(workspace_id):
            raise WorkspaceValidationError("Only Sellora demo workspaces can be deactivated through this flow")
        membership.workspace.is_active = False
        membership.is_active = False
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Workspace", entity_id=workspace_id, action="DEMO_WORKSPACE_DEACTIVATE", new_value={"is_active": False})
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def _seed_demo_dataset(self, workspace_id: UUID, actor_user_id: UUID) -> None:
        leads = [
            Lead(workspace_id=workspace_id, name="DEMO Лід Instagram Direct", instagram_username="demo_direct", status=LeadStatus.NEW.value, notes="Синтетичний демо-запит без реальних контактів."),
            Lead(workspace_id=workspace_id, name="DEMO Лід Instagram Ads", instagram_username="demo_ads", status=LeadStatus.NEW.value, notes="Синтетичний демо-запит без реальних контактів."),
            Lead(workspace_id=workspace_id, name="DEMO Повторне звернення", instagram_username="demo_repeat", status=LeadStatus.IN_PROGRESS.value),
            Lead(workspace_id=workspace_id, name="DEMO Ручне додавання", instagram_username="demo_manual", status=LeadStatus.IN_PROGRESS.value),
            Lead(workspace_id=workspace_id, name="DEMO Кваліфікований лід", instagram_username="demo_qualified", status=LeadStatus.QUALIFIED.value),
            Lead(workspace_id=workspace_id, name="DEMO Конвертований лід", instagram_username="demo_converted", status=LeadStatus.CONVERTED.value),
        ]
        customers = [
            Customer(workspace_id=workspace_id, name="DEMO Клієнт А", phone="+000000000001", instagram_username="demo_customer_a"),
            Customer(workspace_id=workspace_id, name="DEMO Клієнт B", phone="+000000000002", instagram_username="demo_customer_b"),
            Customer(workspace_id=workspace_id, name="DEMO Повторний клієнт", phone="+000000000003", instagram_username="demo_repeat_customer"),
            Customer(workspace_id=workspace_id, name="DEMO Без замовлень", phone="+000000000004", instagram_username="demo_no_orders"),
        ]
        self.db.add_all(leads + customers)
        self.db.flush()
        products: list[Product] = []
        variants: list[ProductVariant] = []
        inventories: list[Inventory] = []
        transactions: list[InventoryTransaction] = []
        for index, name in enumerate(["Годинник", "Браслет", "Сережки", "Каблучка", "Підвіска", "Комплект"], start=1):
            product = Product(workspace_id=workspace_id, name=f"DEMO {name}", sku=f"DEMO-P{index}", category="demo", is_active=True)
            self.db.add(product)
            self.db.flush()
            variant = ProductVariant(workspace_id=workspace_id, product_id=product.id, sku=f"DEMO-V{index}", color="demo", size="one", price=Decimal("100.00") + index, is_active=True)
            self.db.add(variant)
            self.db.flush()
            stock = max(0, 8 - index)
            reserved = 1 if index in {1, 2} else 0
            inventory = Inventory(workspace_id=workspace_id, product_variant_id=variant.id, stock_quantity=stock, reserved_quantity=reserved, minimum_quantity=2)
            self.db.add(inventory)
            self.db.flush()
            transaction = InventoryTransaction(workspace_id=workspace_id, inventory_id=inventory.id, product_variant_id=variant.id, transaction_type=InventoryTransactionType.STOCK_IN.value, quantity=stock, previous_stock_quantity=0, new_stock_quantity=stock, previous_reserved_quantity=0, new_reserved_quantity=reserved, reason="Sprint 8B synthetic demo dataset", created_by=actor_user_id)
            products.append(product)
            variants.append(variant)
            inventories.append(inventory)
            transactions.append(transaction)
        self.db.add_all(transactions)
        self.db.flush()
        statuses = [OrderStatus.NEW, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]
        for index, status in enumerate(statuses, start=1):
            variant = variants[index - 1]
            amount = Decimal("100.00") + index
            order = Order(workspace_id=workspace_id, order_number=f"DEMO-8B-{uuid4().hex[:8]}", customer_id=customers[(index - 1) % 3].id, status=status.value, payment_status=PaymentStatus.PAID.value if status in {OrderStatus.DELIVERED, OrderStatus.SHIPPED} else PaymentStatus.PENDING.value, revenue=amount, product_cost=Decimal("45.00"), net_profit=amount - Decimal("45.00"))
            self.db.add(order)
            self.db.flush()
            self.db.add(OrderItem(workspace_id=workspace_id, order_id=order.id, product_variant_id=variant.id, sku=variant.sku, product_name=variant.product.name if variant.product else variant.sku, quantity=1, unit_price=amount, unit_cost=Decimal("45.00"), line_total=amount, line_cost=Decimal("45.00")))
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Workspace", entity_id=workspace_id, action=DEMO_WORKSPACE_CREATE_ACTION, new_value={"dataset": "Sprint 8B synthetic demo dataset", "provenance_version": 1})

    def get_settings(self, workspace_id: UUID) -> Workspace | None:
        if hasattr(self, "workspaces"):
            return self.workspaces.get_workspace(workspace_id)
        return self.db.get(Workspace, workspace_id)

    def get_current_workspace(self, workspace_id: UUID, actor_user_id: UUID) -> WorkspaceUser | None:
        return self.workspaces.get_active_membership(workspace_id, actor_user_id)

    def require_owner(self, workspace_id: UUID, actor_user_id: UUID) -> WorkspaceUser:
        membership = self.workspaces.get_active_membership(workspace_id, actor_user_id)
        if membership is None or membership.role.name != RoleName.OWNER.value:
            raise WorkspacePermissionError("Insufficient workspace permissions")
        return membership

    def update_settings(self, workspace_id: UUID, payload: WorkspaceSettingsUpdate, actor_user_id: UUID | None) -> Workspace | None:
        if actor_user_id is not None and hasattr(self, "workspaces"):
            self.require_owner(workspace_id, actor_user_id)
        workspace = self.get_settings(workspace_id)
        if workspace is None or not workspace.is_active:
            return None
        changes = payload.model_dump(exclude_unset=True)
        if "slug" in changes and changes["slug"] is not None:
            existing = self.workspaces.get_by_slug(changes["slug"]) if hasattr(self, "workspaces") else None
            if existing and existing.id != workspace_id:
                raise WorkspaceValidationError("Workspace slug already exists")
        old_value = snapshot(workspace)
        currency_changed = "currency_code" in changes and changes["currency_code"] is not None and changes["currency_code"].value != workspace.currency_code
        if "name" in changes and changes["name"] is not None:
            workspace.name = changes["name"].strip()
        if "slug" in changes and changes["slug"] is not None:
            workspace.slug = changes["slug"]
        if "currency_code" in changes and changes["currency_code"] is not None:
            workspace.currency_code = changes["currency_code"].value
        if "timezone" in changes and changes["timezone"] is not None:
            workspace.timezone = changes["timezone"]
        action = "WORKSPACE_CURRENCY_UPDATE" if currency_changed else "WORKSPACE_UPDATE"
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Workspace", entity_id=workspace.id, action=action, old_value=old_value, new_value=snapshot(workspace))
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def list_workspace_users(self, workspace_id: UUID, actor_user_id: UUID) -> list[WorkspaceUser]:
        self.require_owner(workspace_id, actor_user_id)
        return self.workspaces.list_members(workspace_id)

    def add_workspace_user(self, workspace_id: UUID, payload: WorkspaceUserCreate, actor_user_id: UUID) -> WorkspaceUser:
        self.require_owner(workspace_id, actor_user_id)
        user = self.users.get_by_email(payload.email)
        if user is not None and self.workspaces.get_membership(workspace_id, user.id) is not None:
            raise WorkspaceValidationError(DUPLICATE_USER_MESSAGE)
        try:
            if user is None:
                parts = payload.full_name.strip().split(maxsplit=1)
                user = self.users.create(email=payload.email, password_hash=hash_password(payload.temporary_password), first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "")
            membership = self.workspaces.add_membership(workspace_id=workspace_id, user_id=user.id, role=payload.role)
            self.db.commit()
            return membership
        except IntegrityError as exc:
            self.db.rollback()
            raise WorkspaceValidationError(DUPLICATE_USER_MESSAGE) from exc
        except Exception:
            self.db.rollback()
            raise

    def change_user_role(self, workspace_id: UUID, target_user_id: UUID, role: RoleName, actor_user_id: UUID) -> WorkspaceUser:
        self.require_owner(workspace_id, actor_user_id)
        membership = self.workspaces.get_active_membership(workspace_id, target_user_id)
        if membership is None:
            raise WorkspaceValidationError("Workspace user not found")
        if membership.role.name == RoleName.OWNER.value and role != RoleName.OWNER and self.workspaces.count_active_owners(workspace_id) <= 1:
            raise WorkspaceValidationError(LAST_OWNER_ROLE_MESSAGE)
        role_model = self.workspaces.get_role(role)
        if role_model is None:
            raise WorkspaceValidationError("Role not found")
        membership.role_id = role_model.id
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def deactivate_user(self, workspace_id: UUID, target_user_id: UUID, actor_user_id: UUID) -> WorkspaceUser:
        self.require_owner(workspace_id, actor_user_id)
        membership = self.workspaces.get_active_membership(workspace_id, target_user_id)
        if membership is None:
            raise WorkspaceValidationError("Workspace user not found")
        if membership.role.name == RoleName.OWNER.value and self.workspaces.count_active_owners(workspace_id) <= 1:
            raise WorkspaceValidationError(LAST_OWNER_DEACTIVATE_MESSAGE)
        membership.is_active = False
        self.db.commit()
        self.db.refresh(membership)
        return membership
