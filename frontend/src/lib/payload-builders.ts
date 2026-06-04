import {
  cleanOptionalDate,
  cleanOptionalEnum,
  cleanOptionalInteger,
  cleanOptionalNumber,
  cleanOptionalString,
  cleanOptionalUuid,
  cleanRequiredInteger,
  cleanRequiredNumber,
  cleanRequiredString,
  stripUndefinedFields,
} from "@/lib/payload-normalizers";
import { LeadCreatePayload } from "@/services/crm";
import { OrderCreatePayload } from "@/services/orders";
import { ProductCreatePayload, ProductVariantCreatePayload } from "@/services/products";
import { AdCampaignCreate, AdMetricCreate } from "@/types/advertising";
import { PaymentStatus } from "@/types/orders";
import { ShipmentCarrier, ShipmentCreatePayload, ShipmentStatus } from "@/types/shipments";

const PAYMENT_STATUSES: PaymentStatus[] = ["PENDING", "PAID", "COD", "REFUNDED"];
const SHIPMENT_CARRIERS: ShipmentCarrier[] = ["NOVA_POSHTA", "UKRPOSHTA", "MEEST", "ROZETKA_DELIVERY", "OTHER"];
const SHIPMENT_STATUSES: ShipmentStatus[] = ["DRAFT", "CREATED", "IN_TRANSIT", "ARRIVED", "DELIVERED", "RETURNED", "CANCELLED"];
const AD_PLATFORMS = ["META", "INSTAGRAM", "FACEBOOK", "TIKTOK", "GOOGLE", "TELEGRAM", "OTHER"] as const;
const AD_CAMPAIGN_STATUSES = ["ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"] as const;
const AD_OBJECTIVES = ["MESSAGES", "SALES", "TRAFFIC", "AWARENESS", "FOLLOWERS", "OTHER"] as const;
const AD_BUDGET_TYPES = ["DAILY", "LIFETIME", "MANUAL"] as const;

type RawLeadValues = Partial<Record<keyof LeadCreatePayload, string | number | null | undefined>> & { name?: string };

export function buildLeadCreatePayload(values: RawLeadValues): LeadCreatePayload {
  return {
    instagram_username: cleanOptionalString(values.instagram_username),
    instagram_profile_url: cleanOptionalString(values.instagram_profile_url),
    name: cleanRequiredString(values.name),
    phone: cleanOptionalString(values.phone),
    lead_source_id: cleanOptionalUuid(values.lead_source_id),
    notes: cleanOptionalString(values.notes),
    assigned_user_id: cleanOptionalUuid(values.assigned_user_id),
    expected_revenue: cleanOptionalNumber(values.expected_revenue),
    first_contact_at: cleanOptionalDate(values.first_contact_at),
    last_contact_at: cleanOptionalDate(values.last_contact_at),
  };
}

type RawProductValues = Partial<ProductCreatePayload> & { image_url?: string };

export function buildProductCreatePayload(values: RawProductValues): ProductCreatePayload {
  const imageUrl = cleanOptionalString(values.image_url);
  return {
    name: cleanRequiredString(values.name),
    sku: cleanOptionalString(values.sku),
    description: cleanOptionalString(values.description),
    category: cleanOptionalString(values.category),
    brand: cleanOptionalString(values.brand),
    is_active: values.is_active ?? true,
    images: imageUrl ? [{ image_url: imageUrl, sort_order: 0, is_primary: true }] : [],
  };
}

type RawProductVariantValues = Partial<Record<keyof ProductVariantCreatePayload, string | number | null | undefined>>;

export function buildProductVariantCreatePayload(values: RawProductVariantValues): ProductVariantCreatePayload {
  return {
    product_id: cleanOptionalUuid(values.product_id) ?? "",
    sku: cleanRequiredString(values.sku),
    color: cleanOptionalString(values.color),
    size: cleanOptionalString(values.size),
    price: cleanOptionalNumber(values.price),
    barcode: cleanOptionalString(values.barcode),
    is_active: values.is_active === undefined ? true : Boolean(values.is_active),
    initial_stock_quantity: Math.max(0, cleanRequiredInteger(values.initial_stock_quantity)),
    minimum_quantity: Math.max(0, cleanRequiredInteger(values.minimum_quantity)),
  };
}

type RawCustomerValues = {
  name?: string;
  phone?: string;
  instagram_username?: string;
  city?: string;
  region?: string;
};

export function buildCustomerCreatePayload(values: RawCustomerValues) {
  return {
    name: cleanRequiredString(values.name),
    phone: cleanOptionalString(values.phone),
    instagram_username: cleanOptionalString(values.instagram_username),
    city: cleanOptionalString(values.city),
    region: cleanOptionalString(values.region),
  };
}

type RawOrderValues = {
  customer_id?: string | null;
  payment_status?: string;
  items?: { product_variant_id?: string; quantity?: string | number; unit_price?: string | number; unit_cost?: string | number }[];
  ad_cost?: string | number;
  shipping_cost?: string | number;
  cod_fee?: string | number;
  other_cost?: string | number;
  notes?: string;
};

export function buildOrderCreatePayload(values: RawOrderValues): OrderCreatePayload {
  const items = (values.items ?? []).map((item) => ({
    product_variant_id: cleanOptionalUuid(item.product_variant_id) ?? "",
    quantity: Math.max(1, cleanRequiredInteger(item.quantity)),
    unit_price: Math.max(0, cleanRequiredNumber(item.unit_price)),
    unit_cost: Math.max(0, cleanRequiredNumber(item.unit_cost)),
  }));

  return {
    customer_id: cleanOptionalUuid(values.customer_id),
    payment_status: cleanOptionalEnum(values.payment_status, PAYMENT_STATUSES) ?? "PENDING",
    items,
    ad_cost: Math.max(0, cleanRequiredNumber(values.ad_cost)),
    shipping_cost: Math.max(0, cleanRequiredNumber(values.shipping_cost)),
    cod_fee: Math.max(0, cleanRequiredNumber(values.cod_fee)),
    other_cost: Math.max(0, cleanRequiredNumber(values.other_cost)),
    notes: cleanOptionalString(values.notes),
  };
}

type RawShipmentValues = Partial<Record<keyof ShipmentCreatePayload, string | number | null | undefined>>;

export function buildShipmentCreatePayload(values: RawShipmentValues): ShipmentCreatePayload {
  return stripUndefinedFields({
    order_id: cleanOptionalUuid(values.order_id) ?? "",
    customer_id: cleanOptionalUuid(values.customer_id),
    tracking_number: cleanOptionalString(values.tracking_number),
    carrier: cleanOptionalEnum(values.carrier, SHIPMENT_CARRIERS) ?? "NOVA_POSHTA",
    status: cleanOptionalEnum(values.status, SHIPMENT_STATUSES) ?? "DRAFT",
    recipient_name: cleanOptionalString(values.recipient_name),
    recipient_phone: cleanOptionalString(values.recipient_phone),
    city: cleanOptionalString(values.city),
    warehouse: cleanOptionalString(values.warehouse),
    nova_poshta_city_ref: cleanOptionalString(values.nova_poshta_city_ref),
    nova_poshta_warehouse_ref: cleanOptionalString(values.nova_poshta_warehouse_ref),
    shipping_cost: cleanOptionalNumber(values.shipping_cost),
    cod_amount: cleanOptionalNumber(values.cod_amount),
    declared_value: cleanOptionalNumber(values.declared_value),
    notes: cleanOptionalString(values.notes),
  });
}

export function buildAdCampaignCreatePayload(values: Record<string, string | number | null | undefined>): AdCampaignCreate {
  return {
    name: cleanRequiredString(values.name),
    platform: cleanOptionalEnum(values.platform, AD_PLATFORMS) ?? "INSTAGRAM",
    status: cleanOptionalEnum(values.status, AD_CAMPAIGN_STATUSES) ?? "ACTIVE",
    objective: cleanOptionalEnum(values.objective, AD_OBJECTIVES) ?? "MESSAGES",
    budget_type: cleanOptionalEnum(values.budget_type, AD_BUDGET_TYPES) ?? "MANUAL",
    daily_budget: cleanOptionalNumber(values.daily_budget),
    total_budget: cleanOptionalNumber(values.total_budget),
    start_date: cleanOptionalDate(values.start_date),
    end_date: cleanOptionalDate(values.end_date),
    notes: cleanOptionalString(values.notes),
  };
}

export function buildAdMetricCreatePayload(values: Record<string, string | number | null | undefined>): AdMetricCreate {
  return {
    campaign_id: cleanOptionalUuid(values.campaign_id) ?? "",
    metric_date: cleanOptionalDate(values.metric_date)?.slice(0, 10) ?? "",
    spend: Math.max(0, cleanRequiredNumber(values.spend)),
    impressions: Math.max(0, cleanRequiredInteger(values.impressions)),
    reach: Math.max(0, cleanRequiredInteger(values.reach)),
    clicks: Math.max(0, cleanRequiredInteger(values.clicks)),
    messages: Math.max(0, cleanRequiredInteger(values.messages)),
    leads: Math.max(0, cleanRequiredInteger(values.leads)),
    orders: Math.max(0, cleanRequiredInteger(values.orders)),
    revenue: Math.max(0, cleanRequiredNumber(values.revenue)),
    net_profit: cleanRequiredNumber(values.net_profit),
  };
}
