export type FinancePeriod = {
  date_from: string;
  date_to: string;
};

export type FinanceDataQualityWarning = {
  code: string;
  message: string;
  message_uk: string;
};

export type FinanceAdjustmentType = "EXPENSE" | "REFUND" | "DISCOUNT" | "FEE" | "SHIPPING_ADJUSTMENT" | "CORRECTION" | "OTHER";
export type FinanceAdjustmentCategory = "PACKAGING" | "DELIVERY" | "PAYMENT_FEE" | "MARKETPLACE_FEE" | "TOOLS" | "SALARY" | "RENT" | "REFUND" | "DISCOUNT" | "ADJUSTMENT" | "OTHER";

export type FinanceAdjustment = {
  id: string;
  workspace_id: string;
  type: FinanceAdjustmentType;
  category: FinanceAdjustmentCategory;
  amount: string;
  currency: string;
  occurred_at: string;
  title: string;
  description: string | null;
  order_id: string | null;
  source: "MANUAL";
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type FinanceAdjustmentPayload = {
  type: FinanceAdjustmentType;
  category: FinanceAdjustmentCategory;
  amount: string;
  currency: string;
  occurred_at: string;
  title: string;
  description?: string | null;
  order_id?: string | null;
};

export type FinanceAdjustmentList = {
  items: FinanceAdjustment[];
  total: number;
  limit: number;
  offset: number;
};

export type FinanceBreakdownItem = {
  key: string;
  label: string;
  amount: string;
  direction: "income" | "expense" | "result" | string;
  share_of_revenue: string | null;
};

export type FinanceComparisonMetric = {
  current: string | number | null;
  previous: string | number | null;
  change: string | null;
  change_percent: string | null;
};

export type FinancePeriodComparison = {
  current_period: FinancePeriod;
  previous_period: FinancePeriod;
  revenue_change: FinanceComparisonMetric;
  gross_profit_change: FinanceComparisonMetric;
  net_profit_change: FinanceComparisonMetric;
  orders_count_change: FinanceComparisonMetric;
  ad_spend_change: FinanceComparisonMetric;
  profit_margin_change: FinanceComparisonMetric;
};

export type FinanceSummary = {
  period: FinancePeriod;
  revenue: string;
  cogs: string;
  gross_profit: string;
  ad_spend: string;
  shipping_cost: string;
  discounts: string;
  refunds: string;
  other_expenses: string;
  manual_expenses: string;
  manual_refunds: string;
  manual_discounts: string;
  manual_fees: string;
  finance_adjustments_total: string;
  net_profit: string;
  profit_margin: string | null;
  orders_count: number;
  paid_orders_count: number;
  average_order_value: string | null;
  breakdown: FinanceBreakdownItem[];
  data_quality_warnings: FinanceDataQualityWarning[];
};
