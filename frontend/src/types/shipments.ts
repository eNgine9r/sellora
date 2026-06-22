export type ShipmentCarrier = "NOVA_POSHTA" | "UKRPOSHTA" | "MEEST" | "ROZETKA_DELIVERY" | "OTHER";
export type ShipmentStatus = "DRAFT" | "CREATED" | "IN_TRANSIT" | "ARRIVED" | "DELIVERED" | "RETURNED" | "CANCELLED";

export type Shipment = {
  id: string;
  workspace_id: string;
  order_id: string;
  customer_id: string | null;
  tracking_number: string | null;
  carrier: ShipmentCarrier;
  status: ShipmentStatus;
  recipient_name: string | null;
  recipient_phone: string | null;
  city: string | null;
  warehouse: string | null;
  shipping_cost: string | null;
  cod_amount: string | null;
  declared_value: string | null;
  notes: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  returned_at: string | null;
  external_provider: string | null;
  external_ref: string | null;
  external_status: string | null;
  nova_poshta_city_ref: string | null;
  nova_poshta_warehouse_ref: string | null;
  nova_poshta_document_ref: string | null;
  nova_poshta_document_number: string | null;
  nova_poshta_raw_status: string | null;
  nova_poshta_synced_at: string | null;
  order_number: string | null;
  order_status: string | null;
  order_payment_status: string | null;
  order_total: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  customer_instagram_username: string | null;
  created_at: string;
  updated_at: string;
};

export type ShipmentCreatePayload = {
  order_id: string;
  customer_id: string | null;
  tracking_number: string | null;
  carrier: ShipmentCarrier;
  status: ShipmentStatus;
  recipient_name: string | null;
  recipient_phone: string | null;
  city: string | null;
  warehouse: string | null;
  shipping_cost: number | null;
  cod_amount: number | null;
  declared_value: number | null;
  notes: string | null;
  nova_poshta_city_ref?: string | null;
  nova_poshta_warehouse_ref?: string | null;
};

export type ShipmentSummary = {
  in_transit_count: number;
  arrived_count: number;
  delivered_today: number;
  returned_this_month: number;
};
