// Synthetic responses follow the existing Order/Shipment/customer-automation contracts.
export function createFulfillmentFixture({ workspaceId, conversationId }) {
  const customerId = "55555555-5555-4555-8555-555555555555";
  const productId = "66666666-6666-4666-8666-666666666666";
  const variantId = "77777777-7777-4777-8777-777777777777";
  const orderId = "88888888-8888-4888-8888-888888888888";
  const shipmentId = "99999999-9999-4999-8999-999999999999";
  const timestamp = "2026-10-19T10:00:00Z";
  const customer = { id: customerId, workspace_id: workspaceId, name: "Олена Тестова", phone: "+380671234567", instagram_username: "olena_fixture", city: "Київ", region: null, total_orders: 0, total_spent: "0", created_at: timestamp, updated_at: timestamp };
  const order = { id: orderId, workspace_id: workspaceId, order_number: "SYN-1001", customer_id: customerId, campaign_id: null, campaign_name: null, customer_name: customer.name, customer_phone: customer.phone, status: "NEW", payment_status: "COD", revenue: "300", product_cost: "120", ad_cost: "10", shipping_cost: "5", cod_fee: "2", other_cost: "3", net_profit: "160", notes: null, items: [], status_history: [], created_at: timestamp, updated_at: timestamp };
  const shipment = { id: shipmentId, workspace_id: workspaceId, order_id: orderId, customer_id: customerId, tracking_number: "20400000000000", carrier: "NOVA_POSHTA", status: "CREATED", recipient_name: customer.name, recipient_phone: customer.phone, city: "Київ", warehouse: "Відділення №1", shipping_cost: "5", cod_amount: "300", declared_value: "300", notes: null, shipped_at: null, delivered_at: null, returned_at: null, external_provider: "NOVA_POSHTA", external_ref: "synthetic-document", external_status: null, nova_poshta_city_ref: "synthetic-city", nova_poshta_warehouse_ref: "synthetic-warehouse", nova_poshta_document_ref: "synthetic-document", nova_poshta_document_number: "20400000000000", nova_poshta_create_state: "COMPLETED", nova_poshta_manual_reconciliation_required: false, nova_poshta_last_error_code: null, order_number: order.order_number, order_status: order.status, order_payment_status: order.payment_status, order_total: "300", customer_name: customer.name, customer_phone: customer.phone, customer_instagram_username: customer.instagram_username, created_at: timestamp, updated_at: timestamp };
  const state = { linked: false, created: false, payloads: [], invalidRelation: false, failReads: false, noShipment: false, readWorkspaces: [], proposal: null, proposalError: false, proposalRequests: 0, holdProposal: false, releaseProposal: null, extraVariants: [], extraInventory: [], extraOrders: [], orderListRequests: 0, orderDetailRequests: 0, holdOrderDetail: false, releaseOrderDetail: null, orderDetailOverride: null };
  const automation = () => ({ conversation_id: conversationId, customer, linked_order_id: state.linked ? orderId : null, stage: state.linked ? "CUSTOMER_READY" : "PROSPECT_READY_FOR_ORDER", missing_fields: [], can_create_order: !state.linked, profile_complete: true, created_automatically: false });
  return {
    state, customerId, productId, variantId, orderId, shipmentId, order, shipment,
    conversations: (items) => items.map((item) => item.id === conversationId ? { ...item, linked_customer_id: customerId, linked_order_id: state.linked ? orderId : null } : item),
    async handle({ key, requestWorkspace, respond, request }) {
      const send = async (data, status) => { await respond(data, status); return true; };
      if (key === `GET /api/v1/direct/conversations/${conversationId}/order-proposal`) {
        state.proposalRequests++;
        if (state.holdProposal) await new Promise((resolve) => { state.releaseProposal = resolve; });
        if (requestWorkspace !== workspaceId) return send({ detail: "Synthetic unavailable" }, 404);
        if (state.proposalError) return send({ detail: "Synthetic proposal unavailable" }, 503);
        return send(state.proposal ?? { conversation_id: conversationId, analysis_id: null, analysis_created_at: null, analysis_context_message_id: null, analysis_state: "MISSING", catalog_truncated: false, context_truncated: false, lines: [] });
      }
      if (key === `GET /api/v1/direct/conversations/${conversationId}/customer-automation`) return send(automation());
      if (key === `POST /api/v1/direct/conversations/${conversationId}/customer-automation/finalize-order`) { state.linked = true; return send(automation()); }
      if (key === "GET /api/v1/customers") return send([customer]);
      if (key === `GET /api/v1/customers/${customerId}/addresses`) return send([]);
      if (key === "GET /api/v1/products") return send([{ id: productId, workspace_id: workspaceId, name: "Синтетичний светр", sku: "SYN", is_active: true }]);
      if (key === "GET /api/v1/products/variants") return send([{ id: variantId, workspace_id: workspaceId, product_id: productId, sku: "SYN-M", price: "100", is_active: true }, ...state.extraVariants]);
      if (key === "GET /api/v1/inventory") return send([{ id: "synthetic-inventory", product_variant_id: variantId, stock_quantity: 20, reserved_quantity: 0 }, ...state.extraInventory]);
      if (key === "GET /api/v1/orders") {
        state.orderListRequests++;
        const status = new URL(request.url()).searchParams.get("status");
        return send([...(state.linked || state.created ? [order] : []), ...state.extraOrders].filter((item) => !status || item.status === status));
      }
      if (key === "GET /api/v1/shipments") return send([shipment]);
      if (key === "GET /api/v1/shipments/summary") return send({ in_transit_count: 0, arrived_count: 0, delivered_today: 0, returned_this_month: 0 });
      if (key === "GET /api/v1/integrations/nova-poshta/readiness") return send({ provider_writes_enabled: true, write_blockers: [] });
      if (key === "GET /api/v1/integrations/nova-poshta/cities") return send([{ ref: "synthetic-city", description: "Київ" }]);
      if (key === "GET /api/v1/integrations/nova-poshta/warehouses") return send([{ ref: "synthetic-warehouse", description: "Відділення №1", number: "1" }]);
      if ([`GET /api/v1/orders/${orderId}`, `GET /api/v1/shipments/${shipmentId}`, `GET /api/v1/orders/${orderId}/shipment`].includes(key)) {
        state.readWorkspaces.push(requestWorkspace);
        if (key === `GET /api/v1/orders/${orderId}`) {
          state.orderDetailRequests++;
          if (state.holdOrderDetail && requestWorkspace === workspaceId) await new Promise((resolve) => { state.releaseOrderDetail = resolve; });
        }
        if (requestWorkspace !== workspaceId || state.failReads) return send({ detail: "Synthetic unavailable" }, 404);
        if (key.endsWith("/shipment")) return send(state.noShipment ? null : shipment);
        if (key.includes("/shipments/")) return send(state.invalidRelation ? { ...shipment, order_id: "different-order" } : shipment);
        return send(state.orderDetailOverride ?? order);
      }
      if (key === "POST /api/v1/order-fulfillments") {
        state.created = true;
        state.payloads.push(JSON.parse(request.postData()));
        return send({ result_code: "ORDER_AND_TTN_CREATED", idempotency_key: state.payloads.at(-1).idempotency_key, idempotent_replay: false, order, shipment, tracking_number: shipment.tracking_number, provider_error_code: null, retry_available: false, message: "Synthetic success" });
      }
      return false;
    },
  };
}
