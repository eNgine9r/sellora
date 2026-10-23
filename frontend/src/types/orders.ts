export type OrderStatus = "NEW" | "CONFIRMED" | "SHIPPED" | "DELIVERED" | "COMPLETED" | "RETURNED" | "CANCELLED";
export type PaymentStatus = "PENDING" | "PAID" | "COD" | "REFUNDED";
export type HistoricalCostSource = "SHEET_ROW_MATCH" | "PRICE_MEDIAN" | "PRICE_BAND" | "MANUAL";
export type HistoricalCostConfidence = "MULTI_SIGNAL_MATCH" | "PRICE_ONLY" | "LOW" | "MANUAL_REVIEW";

export type HistoricalEstimatedCostPayload = {
  amount: number;
  source: HistoricalCostSource;
  reference: string | null;
};

export type OrderItem = {
  id: string;
  workspace_id: string;
  order_id: string;
  product_variant_id: string;
  sku: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  unit_cost: string;
  line_total: string;
  line_cost: string;
};

export type OrderStatusHistory = {
  id: string;
  workspace_id: string;
  order_id: string;
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  changed_by: string | null;
  note: string | null;
  created_at: string;
};

export type Order = {
  id: string;
  workspace_id: string;
  order_number: string;
  customer_id: string | null;
  campaign_id: string | null;
  campaign_name: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  customer_instagram_username: string | null;
  status: OrderStatus;
  payment_status: PaymentStatus;
  is_historical: boolean;
  revenue: string;
  product_cost: string;
  estimated_product_cost: string | null;
  estimated_cost_source: HistoricalCostSource | null;
  estimated_cost_confidence: HistoricalCostConfidence | null;
  estimated_cost_reference: string | null;
  ad_cost: string;
  shipping_cost: string;
  cod_fee: string;
  other_cost: string;
  net_profit: string;
  notes: string | null;
  completed_at: string | null;
  items: OrderItem[];
  status_history: OrderStatusHistory[];
  created_at: string;
  updated_at: string;
};

export type OrderDashboard = {
  orders_today: number;
  revenue_today: string;
  profit_today: string;
};
