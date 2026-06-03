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
  order_number: string | null;
  customer_name: string | null;
  created_at: string;
  updated_at: string;
};

export type ShipmentCreatePayload = {
  order_id: string;
  customer_id?: string | null;
  tracking_number?: string;
  carrier?: ShipmentCarrier;
  status?: ShipmentStatus;
  recipient_name?: string;
  recipient_phone?: string;
  city?: string;
  warehouse?: string;
  shipping_cost?: string;
  cod_amount?: string;
  declared_value?: string;
  notes?: string;
};

export type ShipmentSummary = {
  in_transit_count: number;
  arrived_count: number;
  delivered_today: number;
  returned_this_month: number;
};
