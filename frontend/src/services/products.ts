import { apiRequest } from "@/services/api";
import { Inventory, InventoryTransaction, InventoryTransactionType, Product, ProductVariant } from "@/types/products";

function workspaceHeaders(workspaceId: string, token?: string): HeadersInit {
  return {
    "X-Workspace-ID": workspaceId,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export type ProductCreatePayload = {
  name: string;
  sku?: string;
  description?: string;
  images?: { image_url: string; alt_text?: string; is_primary?: boolean }[];
};

export type ProductVariantCreatePayload = {
  product_id: string;
  sku: string;
  color?: string;
  size?: string;
  price?: string;
  initial_stock_quantity?: number;
  minimum_quantity?: number;
};

export async function fetchProducts(workspaceId: string, search?: string, token?: string): Promise<Product[]> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
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
  if (productId) params.set("product_id", productId);
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
  if (inventoryId) params.set("inventory_id", inventoryId);
  const query = params.toString();
  return apiRequest<InventoryTransaction[]>(`/inventory/transactions${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId, token) });
}

export async function createInventoryTransaction(
  workspaceId: string,
  inventoryId: string,
  payload: { transaction_type: InventoryTransactionType; quantity: number; reason?: string },
  token?: string,
): Promise<InventoryTransaction> {
  return apiRequest<InventoryTransaction>(`/inventory/${inventoryId}/transactions`, {
    method: "POST",
    headers: workspaceHeaders(workspaceId, token),
    body: JSON.stringify(payload),
  });
}
