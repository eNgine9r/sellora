import { Order, PaymentStatus } from "@/types/orders";
import { Shipment } from "@/types/shipments";

export type OrderFulfillmentResultCode =
  | "ORDER_AND_TTN_CREATED"
  | "ORDER_CREATED_TTN_PENDING"
  | "ORDER_CREATED_PROVIDER_RECONCILIATION_REQUIRED";

export type OrderFulfillmentPayload = {
  idempotency_key: string;
  customer_id: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  instagram_username: string | null;
  address_id: string | null;
  recipient_name: string;
  recipient_phone: string;
  nova_poshta_city_ref: string;
  city: string;
  nova_poshta_warehouse_ref: string;
  warehouse: string;
  warehouse_number: string | null;
  save_address_as_default: boolean;
  items: { product_variant_id: string; quantity: number; unit_price: number; unit_cost: number }[];
  payment_status: Exclude<PaymentStatus, "REFUNDED">;
  cod_amount: number | null;
  declared_value: number | null;
  campaign_id: string | null;
  ad_cost: number;
  shipping_cost: number;
  cod_fee: number;
  other_cost: number;
  notes: string | null;
  create_ttn: boolean;
};

export type OrderFulfillmentResult = {
  result_code: OrderFulfillmentResultCode;
  idempotency_key: string;
  idempotent_replay: boolean;
  order: Order;
  shipment: Shipment;
  tracking_number: string | null;
  provider_error_code: string | null;
  retry_available: boolean;
  message: string;
};

export type FulfillmentOperationState =
  | "PENDING"
  | "VALIDATING"
  | "RESERVING_STOCK"
  | "STOCK_RESERVED"
  | "CREATING_SHIPMENT"
  | "SHIPMENT_READY"
  | "PROVIDER_REQUESTING"
  | "PROVIDER_RESULT_RECEIVED"
  | "PERSISTING_RESULT"
  | "COMPLETED"
  | "FAILED_SAFE"
  | "RECONCILIATION_REQUIRED"
  | "RECONCILING"
  | "CANCELLED";

export type FulfillmentRequest = {
  customer_id: string | null;
  address_id: string | null;
  recipient: { name: string; phone: string };
  delivery: {
    provider: "NOVA_POSHTA";
    city_ref: string;
    city_description: string;
    warehouse_ref: string;
    warehouse_description: string;
    warehouse_number: string | null;
    service_type: string;
    payer_type: string;
    payment_method: string;
    declared_value: number;
    weight: number;
    place_count: number;
    cargo_description: string;
  };
  payment: { mode: "COD" | "PREPAID_OR_COD" | "PREPAID"; already_paid: number; cod_amount: number };
};

export type FulfillmentPrepareResult = {
  ready: boolean;
  blockers: string[];
  warnings: string[];
  inventory: Record<string, unknown>;
  provider_readiness: Record<string, unknown>;
  finance_preview: Record<string, unknown>;
  existing_operation: { operation_id: string; state: FulfillmentOperationState } | null;
};

export type FulfillmentExecuteResult = {
  operation_id: string;
  state: FulfillmentOperationState;
  result_code: OrderFulfillmentResultCode | null;
  reused: boolean;
  shipment_id: string | null;
  tracking_number: string | null;
  document_ref: string | null;
  manual_reconciliation_required: boolean;
  blind_retry_blocked: boolean;
  inventory_reserved: boolean;
  reservation_verified: boolean;
  retry_available: boolean;
  safe_message: string;
};

export type FulfillmentStatus = Omit<FulfillmentExecuteResult, "reused" | "inventory_reserved" | "reservation_verified" | "retry_available" | "safe_message"> & {
  operation_id: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
};
