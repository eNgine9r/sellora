export type ProductImage = {
  id: string;
  workspace_id: string;
  product_id: string;
  image_url: string;
  alt_text: string | null;
  sort_order: number;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
};

export type Product = {
  id: string;
  workspace_id: string;
  name: string;
  sku: string | null;
  description: string | null;
  is_active: boolean;
  images: ProductImage[];
  created_at: string;
  updated_at: string;
};

export type ProductVariant = {
  id: string;
  workspace_id: string;
  product_id: string;
  sku: string;
  color: string | null;
  size: string | null;
  price: string | null;
  created_at: string;
  updated_at: string;
};

export type Inventory = {
  id: string;
  workspace_id: string;
  product_variant_id: string;
  stock_quantity: number;
  reserved_quantity: number;
  minimum_quantity: number;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
};

export type InventoryTransactionType = "STOCK_IN" | "STOCK_OUT" | "RESERVE" | "UNRESERVE" | "RETURN" | "ADJUSTMENT";

export type InventoryTransaction = {
  id: string;
  workspace_id: string;
  inventory_id: string;
  product_variant_id: string;
  transaction_type: InventoryTransactionType;
  quantity: number;
  previous_stock_quantity: number;
  new_stock_quantity: number;
  previous_reserved_quantity: number;
  new_reserved_quantity: number;
  reason: string | null;
  created_by: string | null;
  created_at: string;
};
