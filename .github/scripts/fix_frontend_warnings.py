from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one match in {path}, found {count}: {old[:100]!r}"
        )
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


analytics = "frontend/src/app/analytics/page.tsx"
replace_once(
    analytics,
    "formatPercentValue, formatSafeRatio, leadsInRange",
    "formatPercentValue, leadsInRange",
)
replace_once(
    analytics,
    'import { fetchAdvertisingReport, fetchBusinessInsights, fetchCustomersReport, fetchCustomersSummary, fetchInventoryReport, fetchInventorySummary, fetchProductsReport, fetchProfitSummary, fetchSalesReport, fetchSalesSummary, fetchSalesTrend, fetchTopProducts } from "@/services/analytics";',
    'import { fetchAdvertisingReport, fetchBusinessInsights, fetchCustomersSummary, fetchInventoryReport, fetchInventorySummary, fetchProfitSummary, fetchSalesReport, fetchSalesSummary, fetchTopProducts } from "@/services/analytics";',
)
replace_once(
    analytics,
    '  const productsReport = useQuery({ queryKey: ["analytics-products-report", workspaceId, startDate, endDate], queryFn: () => fetchProductsReport(workspaceId, undefined, startDate, endDate), enabled });\n',
    "",
)
replace_once(
    analytics,
    '  const customersReport = useQuery({ queryKey: ["analytics-customers-report", workspaceId, startDate, endDate], queryFn: () => fetchCustomersReport(workspaceId, undefined, startDate, endDate), enabled });\n',
    "",
)
replace_once(
    analytics,
    '  const trend = useQuery({ queryKey: ["analytics-trend", workspaceId, startDate, endDate], queryFn: () => fetchSalesTrend(workspaceId, undefined, startDate, endDate), enabled: enabled && canSeeProfit });\n',
    "",
)
replace_once(
    analytics,
    "  const currentOrders = useMemo(() => ordersInRange(orders.data ?? [], range), [orders.data, range.date_from, range.date_to]);",
    "  const currentOrders = useMemo(() => ordersInRange(orders.data ?? [], range), [orders.data, range]);",
)
replace_once(
    analytics,
    "  const currentLeads = useMemo(() => leadsInRange(leads.data ?? [], range), [leads.data, range.date_from, range.date_to]);",
    "  const currentLeads = useMemo(() => leadsInRange(leads.data ?? [], range), [leads.data, range]);",
)
replace_once(
    analytics,
    "    const variant = lookups.variantById.get(item.variant_id);\n",
    "",
)


dashboard = "frontend/src/app/dashboard/page.tsx"
replace_once(
    dashboard,
    "  const currentOrders = useMemo(() => (orders.data ?? []).filter((order) => isInDateRange(order.created_at, range)), [orders.data, range.date_from, range.date_to]);",
    "  const currentOrders = useMemo(() => (orders.data ?? []).filter((order) => isInDateRange(order.created_at, range)), [orders.data, range]);",
)
replace_once(
    dashboard,
    "  const currentLeads = useMemo(() => (leads.data ?? []).filter((lead: Lead) => isInDateRange(lead.created_at, range)), [leads.data, range.date_from, range.date_to]);",
    "  const currentLeads = useMemo(() => (leads.data ?? []).filter((lead: Lead) => isInDateRange(lead.created_at, range)), [leads.data, range]);",
)
replace_once(
    dashboard,
    "  ].filter((item) => item.value > 0), [currentOrders, inventory.data, shipments.data, t]);",
    "  ].filter((item) => item.value > 0), [backendDashboard.data?.inventory.low_stock_count, backendDashboard.data?.inventory.out_of_stock_count, currentOrders, inventory.data, shipments.data, t]);",
)


products_page = "frontend/src/app/products/page.tsx"
replace_once(
    products_page,
    "  const products = productsQuery.data ?? [];\n  const variants = variantsQuery.data ?? [];",
    "  const products = useMemo(() => productsQuery.data ?? [], [productsQuery.data]);\n  const variants = useMemo(() => variantsQuery.data ?? [], [variantsQuery.data]);",
)


remote_image = Path("frontend/src/components/ui/remote-image.tsx")
remote_image.write_text(
    '''type RemoteImageProps = {\n  src: string;\n  alt: string;\n  className?: string;\n};\n\nexport function RemoteImage({ src, alt, className = "" }: RemoteImageProps) {\n  return (\n    <span\n      role="img"\n      aria-label={alt}\n      className={`block bg-cover bg-center bg-no-repeat ${className}`}\n      style={{ backgroundImage: `url(${JSON.stringify(src)})` }}\n    />\n  );\n}\n''',
    encoding="utf-8",
)


top_products = "frontend/src/features/dashboard/components/top-products-card.tsx"
replace_once(
    top_products,
    'import { EmptyState } from "@/components/ui/states";',
    'import { RemoteImage } from "@/components/ui/remote-image";\nimport { EmptyState } from "@/components/ui/states";',
)
replace_once(
    top_products,
    '<img className="h-11 w-11 shrink-0 rounded-xl object-cover" src={product.imageUrl} alt={product.product_name} />',
    '<RemoteImage className="h-11 w-11 shrink-0 rounded-xl" src={product.imageUrl} alt={product.product_name} />',
)


inventory_table = "frontend/src/features/inventory/components/inventory-table.tsx"
replace_once(
    inventory_table,
    'import { useI18n } from "@/i18n/provider";',
    'import { RemoteImage } from "@/components/ui/remote-image";\nimport { useI18n } from "@/i18n/provider";',
)
replace_once(
    inventory_table,
    '<img className="h-12 w-12 rounded-lg object-cover" src={image.image_url} alt={image.alt_text ?? product?.name ?? label} />',
    '<RemoteImage className="h-12 w-12 rounded-lg" src={image.image_url} alt={image.alt_text ?? product?.name ?? label} />',
)
replace_once(
    inventory_table,
    '<img className="h-16 w-16 shrink-0 rounded-xl object-cover" src={image.image_url} alt={image.alt_text ?? product?.name ?? label} />',
    '<RemoteImage className="h-16 w-16 shrink-0 rounded-xl" src={image.image_url} alt={image.alt_text ?? product?.name ?? label} />',
)


order_form = "frontend/src/features/orders/components/order-form.tsx"
replace_once(
    order_form,
    'import { FormEvent, useMemo, useState } from "react";',
    'import { FormEvent, useMemo, useState } from "react";\nimport { RemoteImage } from "@/components/ui/remote-image";',
)
replace_once(
    order_form,
    '''                              <img\n                                className="h-9 w-9 shrink-0 rounded-lg object-cover"\n                                src={image.image_url}\n                                alt={image.alt_text ?? product.name}\n                              />''',
    '''                              <RemoteImage\n                                className="h-9 w-9 shrink-0 rounded-lg"\n                                src={image.image_url}\n                                alt={image.alt_text ?? product.name}\n                              />''',
)


product_table = "frontend/src/features/products/components/product-table.tsx"
replace_once(
    product_table,
    'import { useI18n } from "@/i18n/provider";',
    'import { RemoteImage } from "@/components/ui/remote-image";\nimport { useI18n } from "@/i18n/provider";',
)
replace_once(
    product_table,
    '<img className="h-12 w-12 rounded-lg object-cover" src={image.image_url} alt={image.alt_text ?? product.name} />',
    '<RemoteImage className="h-12 w-12 rounded-lg" src={image.image_url} alt={image.alt_text ?? product.name} />',
)
replace_once(
    product_table,
    '<img className="h-16 w-16 shrink-0 rounded-xl object-cover" src={image.image_url} alt={image.alt_text ?? product.name} />',
    '<RemoteImage className="h-16 w-16 shrink-0 rounded-xl" src={image.image_url} alt={image.alt_text ?? product.name} />',
)


payloads = "frontend/src/lib/payload-builders.ts"
replace_once(
    payloads,
    "  const { images: _images, ...update } = payload;\n  return update;",
    "  const { images, ...update } = payload;\n  void images;\n  return update;",
)
replace_once(
    payloads,
    "  const { product_id: _product_id, initial_stock_quantity: _initial, minimum_quantity: _minimum, ...update } = payload;\n  return update;",
    "  const { product_id, initial_stock_quantity, minimum_quantity, ...update } = payload;\n  void product_id;\n  void initial_stock_quantity;\n  void minimum_quantity;\n  return update;",
)
replace_once(
    payloads,
    '  const { order_id: _order_id, ...payload } = buildShipmentCreatePayload({ ...values, order_id: "00000000-0000-0000-0000-000000000000" });\n  return payload;',
    '  const { order_id, ...payload } = buildShipmentCreatePayload({ ...values, order_id: "00000000-0000-0000-0000-000000000000" });\n  void order_id;\n  return payload;',
)
replace_once(
    payloads,
    '  const { campaign_id: _campaign_id, ...payload } = buildAdMetricCreatePayload({ ...values, campaign_id: "00000000-0000-0000-0000-000000000000" });\n  return payload;',
    '  const { campaign_id, ...payload } = buildAdMetricCreatePayload({ ...values, campaign_id: "00000000-0000-0000-0000-000000000000" });\n  void campaign_id;\n  return payload;',
)


theme_provider = "frontend/src/providers/theme-provider.tsx"
replace_once(
    theme_provider,
    '''function getSystemTheme(): ResolvedTheme {\n  if (typeof window === "undefined") return "light";\n  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";\n}\n\n''',
    "",
)


integrations = Path("frontend/src/services/integrations.ts")
integrations.write_text(
    '''import { apiRequest } from "@/services/api";\nimport { NovaPoshtaActionResponse, NovaPoshtaDirectoryItem, NovaPoshtaSettings, NovaPoshtaSettingsPayload } from "@/types/integrations";\n\nfunction withWorkspaceContext<T>(workspaceId: string, request: () => Promise<T>) {\n  // The active workspace is attached by the shared API client. Keep this argument for a consistent service API.\n  void workspaceId;\n  return request();\n}\n\nexport const fetchNovaPoshtaSettings = (workspaceId: string) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/settings"));\nexport const saveNovaPoshtaSettings = (workspaceId: string, payload: NovaPoshtaSettingsPayload) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/settings", { method: "POST", body: JSON.stringify(payload) }));\nexport const testNovaPoshtaConnection = (workspaceId: string) => withWorkspaceContext(workspaceId, () => apiRequest<{ success: boolean; message: string; status: string }>("/integrations/nova-poshta/test-connection", { method: "POST" }));\nexport const disconnectNovaPoshta = (workspaceId: string) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/disconnect", { method: "DELETE" }));\nexport const searchNovaPoshtaCities = (workspaceId: string, q: string, limit = 20) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/cities?q=${encodeURIComponent(q)}&limit=${limit}`));\nexport const searchNovaPoshtaWarehouses = (workspaceId: string, cityRef: string, q?: string, limit = 50) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/warehouses?city_ref=${encodeURIComponent(cityRef)}${q ? `&q=${encodeURIComponent(q)}` : ""}&limit=${limit}`));\nexport const createNovaPoshtaTtn = (workspaceId: string, shipmentId: string) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/create-ttn`, { method: "POST" }));\nexport const syncNovaPoshtaStatus = (workspaceId: string, shipmentId: string) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/sync-status`, { method: "POST" }));\n''',
    encoding="utf-8",
)


auth_store = "frontend/src/stores/auth.store.tsx"
replace_once(
    auth_store,
    "  }, [currentUser]);\n\n  const currentWorkspace = useMemo",
    "  }, []);\n\n  const currentWorkspace = useMemo",
)
