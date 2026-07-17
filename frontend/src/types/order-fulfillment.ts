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
