export type Tag = { id: string; workspace_id: string; name: string; color: string; created_at: string; updated_at: string };
export type CustomerTag = { id: string; workspace_id: string; customer_id: string; tag_id: string; tag?: Tag | null; created_at: string };
export type CustomerNote = { id: string; workspace_id: string; customer_id: string; note: string; created_by: string | null; created_at: string };
export type CustomerAddress = { id: string; workspace_id: string; customer_id: string; label: string | null; recipient_name: string | null; phone: string | null; address_line1: string; address_line2: string | null; city: string | null; region: string | null; postal_code: string | null; country: string | null; notes: string | null; is_default: boolean; created_at: string; updated_at: string };
export type AttachmentEntityType = "CUSTOMER" | "LEAD" | "ORDER" | "PRODUCT" | "SHIPMENT";
export type Attachment = { id: string; workspace_id: string; entity_type: AttachmentEntityType; entity_id: string; file_url: string; file_name: string | null; content_type: string | null; uploaded_by: string | null; created_at: string };
