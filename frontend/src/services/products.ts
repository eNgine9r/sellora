import { apiRequest } from "@/services/api";
import { Inventory, InventoryTransaction, InventoryTransactionType, Product, ProductVariant } from "@/types/products";

function workspaceHeaders(workspaceId?: string, token?: string): HeadersInit {
  return {
    ...(workspaceId ? { "X-Workspace-ID": workspaceId } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export type ProductCreatePayload = {
  name: string;
  sku: string | null;
  description: string | null;
  category?: string | null;
  brand?: string | null;
  is_active?: boolean;
  images: { image_url: string; alt_text?: string | null; sort_order?: number; is_primary?: boolean }[];
};

export type ProductVariantCreatePayload = {
  product_id: string;
  sku: string;
  color: string | null;
  size: string | null;
  price: number | null;
  barcode?: string | null;
  is_active?: boolean;
  initial_stock_quantity: number;
  minimum_quantity: number;
};

export async function fetchProducts(workspaceId: string, search?: string, token?: string): Promise<Product[]> {
  const params = new URLSearchParams();
  if (search?.trim()) params.set("search", search.trim());
  const query = params.toString();
  return apiRequest<Product[]>(`/products${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId, token) });
}

export async function createProduct(workspaceId: string, payload: ProductCreatePayload, token?: string): Promise<Product> {
  return apiRequest<Product>("/products", {
    method: "POST",
    headers: workspaceHeaders(workspaceId, token),
    body: JSON.stringify(payload),
  });
}

export async function fetchProductVariants(workspaceId: string, productId?: string, token?: string): Promise<ProductVariant[]> {
  const params = new URLSearchParams();
  if (productId?.trim()) params.set("product_id", productId.trim());
  const query = params.toString();
  return apiRequest<ProductVariant[]>(`/products/variants${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId, token) });
}

export async function createProductVariant(workspaceId: string, payload: ProductVariantCreatePayload, token?: string): Promise<ProductVariant> {
  return apiRequest<ProductVariant>("/products/variants", {
    method: "POST",
    headers: workspaceHeaders(workspaceId, token),
    body: JSON.stringify(payload),
  });
}

export async function fetchInventory(workspaceId: string, lowStockOnly = false, token?: string): Promise<Inventory[]> {
  const params = new URLSearchParams();
  if (lowStockOnly) params.set("low_stock_only", "true");
  const query = params.toString();
  return apiRequest<Inventory[]>(`/inventory${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId, token) });
}

export async function fetchInventoryTransactions(workspaceId: string, inventoryId?: string, token?: string): Promise<InventoryTransaction[]> {
  const params = new URLSearchParams();
  if (inventoryId?.trim()) params.set("inventory_id", inventoryId.trim());
  const query = params.toString();
  return apiRequest<InventoryTransaction[]>(`/inventory/transactions${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId, token) });
}

export async function createInventoryTransaction(
  workspaceId: string,
  inventoryId: string,
  payload: { transaction_type: InventoryTransactionType; quantity: number; reason?: string | null },
  token?: string,
): Promise<InventoryTransaction> {
  return apiRequest<InventoryTransaction>(`/inventory/${inventoryId}/transactions`, {
    method: "POST",
    headers: workspaceHeaders(workspaceId, token),
    body: JSON.stringify(payload),
  });
}
