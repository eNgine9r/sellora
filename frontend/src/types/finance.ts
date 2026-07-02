export type FinancePeriod = {
  date_from: string;
  date_to: string;
};

export type FinanceDataQualityWarning = {
  code: string;
  message: string;
  message_uk: string;
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
  net_profit: string;
  profit_margin: string | null;
  orders_count: number;
  paid_orders_count: number;
  average_order_value: string | null;
  data_quality_warnings: FinanceDataQualityWarning[];
};
