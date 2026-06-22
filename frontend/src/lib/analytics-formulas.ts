import { DateRangeValue } from "@/lib/date-range-presets";
import { AdvertisingSummary } from "@/types/advertising";
import { Inventory, Product, ProductVariant } from "@/types/products";
import { Customer, Lead } from "@/types/crm";
import { Order, OrderStatus, PaymentStatus } from "@/types/orders";

export const ANALYTICS_REVENUE_INCLUDED_STATUSES: OrderStatus[] = ["NEW", "CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED"];
export const ANALYTICS_REVENUE_EXCLUDED_STATUSES: OrderStatus[] = ["CANCELLED", "RETURNED"];
export const ANALYTICS_ORDER_STATUSES: OrderStatus[] = ["NEW", "CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED", "RETURNED", "CANCELLED"];
export const ANALYTICS_PAYMENT_STATUSES: PaymentStatus[] = ["PENDING", "PAID", "COD", "REFUNDED"];
export const UNAVAILABLE = "—";

export type SalesReportRow = { date: string; orders: number; revenue: number; netProfit: number; aov: number | null; returns: number; cancelled: number };
export type AnalyticsInsightType = "positive" | "warning" | "critical" | "info";
export type AnalyticsInsight = { type: AnalyticsInsightType; titleKey: string; descriptionKey: string; sourceMetric: string; href?: string; ctaKey?: string; values?: Record<string, string | number> };

export function toFiniteNumber(value?: string | number | null): number {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function safeDivide(numerator: number, denominator: number): number | null {
  if (!denominator) return null;
  const ratio = numerator / denominator;
  return Number.isFinite(ratio) ? ratio : null;
}

export function formatDecimal(value: number | null, digits = 2): string {
  return value == null || !Number.isFinite(value) ? UNAVAILABLE : value.toFixed(digits);
}

export function formatPercentValue(value: number | null, digits = 1): string {
  return value == null || !Number.isFinite(value) ? UNAVAILABLE : `${value.toFixed(digits)}%`;
}

export function formatDeltaPercent(current: number, previous: number): string | undefined {
  const value = safeDivide(current - previous, previous);
  return value == null ? undefined : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
}

export function formatSafeRatio(numerator: number, denominator: number, digits = 2): string {
  return formatDecimal(safeDivide(numerator, denominator), digits);
}

export function isInDateRange(dateValue: string | null | undefined, range: Pick<DateRangeValue, "date_from" | "date_to">): boolean {
  if (!dateValue) return false;
  const dateOnly = dateValue.slice(0, 10);
  return (!range.date_from || dateOnly >= range.date_from) && (!range.date_to || dateOnly <= range.date_to);
}

export function ordersInRange(orders: Order[], range: Pick<DateRangeValue, "date_from" | "date_to">): Order[] {
  return orders.filter((order) => isInDateRange(order.created_at, range));
}

export function leadsInRange(leads: Lead[], range: Pick<DateRangeValue, "date_from" | "date_to">): Lead[] {
  return leads.filter((lead) => isInDateRange(lead.created_at, range));
}

export function revenueOrders(orders: Order[]): Order[] {
  return orders.filter((order) => ANALYTICS_REVENUE_INCLUDED_STATUSES.includes(order.status));
}

export function summarizeOrders(orders: Order[]) {
  const included = revenueOrders(orders);
  const revenue = included.reduce((sum, order) => sum + toFiniteNumber(order.revenue), 0);
  const netProfit = included.reduce((sum, order) => sum + toFiniteNumber(order.net_profit), 0);
  const productCost = included.reduce((sum, order) => sum + toFiniteNumber(order.product_cost), 0);
  const grossProfit = revenue - productCost;
  const aov = safeDivide(revenue, included.length);
  const margin = safeDivide(netProfit * 100, revenue);
  const shippedOrDelivered = orders.filter((order) => ["SHIPPED", "DELIVERED", "COMPLETED", "RETURNED"].includes(order.status)).length;
  const returnedOrders = orders.filter((order) => order.status === "RETURNED").length;
  const returnRate = safeDivide(returnedOrders * 100, shippedOrDelivered);
  const statusCounts = Object.fromEntries(ANALYTICS_ORDER_STATUSES.map((status) => [status, orders.filter((order) => order.status === status).length])) as Record<OrderStatus, number>;
  const paymentCounts = Object.fromEntries(ANALYTICS_PAYMENT_STATUSES.map((status) => [status, orders.filter((order) => order.payment_status === status).length])) as Record<PaymentStatus, number>;
  return { ordersCount: orders.length, includedOrdersCount: included.length, revenue, netProfit, productCost, grossProfit, aov, margin, returnRate, statusCounts, paymentCounts, returnedOrders, cancelledOrders: statusCounts.CANCELLED, deliveredOrders: statusCounts.DELIVERED + statusCounts.COMPLETED };
}

export function buildDailySalesRows(orders: Order[]): SalesReportRow[] {
  const grouped = new Map<string, SalesReportRow>();
  for (const order of orders) {
    const date = order.created_at.slice(0, 10);
    const row = grouped.get(date) ?? { date, orders: 0, revenue: 0, netProfit: 0, aov: null, returns: 0, cancelled: 0 };
    row.orders += 1;
    if (order.status === "RETURNED") row.returns += 1;
    if (order.status === "CANCELLED") row.cancelled += 1;
    if (ANALYTICS_REVENUE_INCLUDED_STATUSES.includes(order.status)) {
      row.revenue += toFiniteNumber(order.revenue);
      row.netProfit += toFiniteNumber(order.net_profit);
    }
    grouped.set(date, row);
  }
  return Array.from(grouped.values()).sort((a, b) => b.date.localeCompare(a.date)).map((row) => ({ ...row, aov: safeDivide(row.revenue, row.orders) }));
}

export function summarizeAdvertising(summary?: AdvertisingSummary | null) {
  const spend = toFiniteNumber(summary?.total_spend);
  const revenue = toFiniteNumber(summary?.total_revenue);
  const orders = summary?.total_orders ?? 0;
  const leads = summary?.total_leads ?? 0;
  return { spend, revenue, roas: safeDivide(revenue, spend), cpa: safeDivide(spend, orders), cpl: safeDivide(spend, leads), messages: summary?.total_messages ?? 0, leads, orders };
}

export function summarizeCustomers(customers: Customer[]) {
  const withOrders = customers.filter((customer) => customer.total_orders > 0);
  const repeat = withOrders.filter((customer) => customer.total_orders >= 2);
  const totalSpent = withOrders.reduce((sum, customer) => sum + toFiniteNumber(customer.total_spent), 0);
  return { totalCustomers: customers.length, customersWithOrders: withOrders.length, repeatCustomers: repeat.length, repeatCustomerRate: safeDivide(repeat.length * 100, withOrders.length), averageSpend: safeDivide(totalSpent, withOrders.length), totalSpent };
}

export function summarizeInventory(items: Inventory[]) {
  return {
    lowStockCount: items.filter((item) => item.stock_quantity <= item.minimum_quantity).length,
    outOfStockCount: items.filter((item) => item.stock_quantity <= 0).length,
    reservedQuantity: items.reduce((sum, item) => sum + item.reserved_quantity, 0),
    incomingQuantity: items.reduce((sum, item) => sum + item.incoming_quantity, 0),
    totalStockUnits: items.reduce((sum, item) => sum + item.stock_quantity, 0),
  };
}

export function buildVariantLookups(products: Product[], variants: ProductVariant[], inventory: Inventory[]) {
  const productById = new Map(products.map((product) => [product.id, product]));
  const variantById = new Map(variants.map((variant) => [variant.id, variant]));
  const inventoryByVariantId = new Map(inventory.map((item) => [item.product_variant_id, item]));
  return { productById, variantById, inventoryByVariantId };
}

export function buildBusinessInsights(input: { orders: Order[]; adSummary?: AdvertisingSummary | null; inventory: Inventory[]; products: Product[]; variants: ProductVariant[]; leads: Lead[] }): AnalyticsInsight[] {
  const orderSummary = summarizeOrders(input.orders);
  const ad = summarizeAdvertising(input.adSummary);
  const inventorySummary = summarizeInventory(input.inventory);
  const insights: AnalyticsInsight[] = [];
  if (inventorySummary.lowStockCount > 0) insights.push({ type: inventorySummary.outOfStockCount > 0 ? "critical" : "warning", titleKey: "analytics.insights.lowStockTitle", descriptionKey: "analytics.insights.lowStockDescription", sourceMetric: "low_stock", href: "/inventory", ctaKey: "analytics.insights.ctaInventory", values: { count: inventorySummary.lowStockCount } });
  if (ad.spend > 0 && ad.orders === 0) insights.push({ type: "critical", titleKey: "analytics.insights.adSpendNoOrdersTitle", descriptionKey: "analytics.insights.adSpendNoOrdersDescription", sourceMetric: "ad_spend_without_orders", href: "/advertising", ctaKey: "analytics.insights.ctaAdvertising" });
  if (ad.roas != null && ad.roas < 1) insights.push({ type: "warning", titleKey: "analytics.insights.lowRoasTitle", descriptionKey: "analytics.insights.lowRoasDescription", sourceMetric: "roas_below_one", href: "/advertising", ctaKey: "analytics.insights.ctaAdvertising" });
  if (orderSummary.cancelledOrders > 0 || orderSummary.returnedOrders > 0) insights.push({ type: "info", titleKey: "analytics.insights.returnsTitle", descriptionKey: "analytics.insights.returnsDescription", sourceMetric: "returns_cancelled", href: "/orders", ctaKey: "analytics.insights.ctaOrders", values: { returns: orderSummary.returnedOrders, cancelled: orderSummary.cancelledOrders } });
  if (input.leads.length > 0 && orderSummary.ordersCount === 0) insights.push({ type: "info", titleKey: "analytics.insights.leadsNoOrdersTitle", descriptionKey: "analytics.insights.leadsNoOrdersDescription", sourceMetric: "leads_without_orders", href: "/leads", ctaKey: "analytics.insights.ctaLeads" });
  if (!insights.length) insights.push({ type: "positive", titleKey: "analytics.insights.healthyTitle", descriptionKey: "analytics.insights.healthyDescription", sourceMetric: "healthy" });
  return insights.slice(0, 6);
}
