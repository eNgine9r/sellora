import { apiRequest } from "@/services/api";
import { Attachment, AttachmentEntityType, CustomerAddress, CustomerNote, CustomerTag, Tag } from "@/types/crm-completion";

function workspaceHeaders(workspaceId: string, token?: string): HeadersInit {
  return { "X-Workspace-ID": workspaceId, ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

export async function fetchTags(workspaceId: string, token?: string): Promise<Tag[]> {
  return apiRequest<Tag[]>("/tags", { headers: workspaceHeaders(workspaceId, token) });
}
export async function createTag(workspaceId: string, payload: { name: string; color: string }, token?: string): Promise<Tag> {
  return apiRequest<Tag>("/tags", { method: "POST", headers: workspaceHeaders(workspaceId, token), body: JSON.stringify(payload) });
}
export async function fetchCustomerTags(workspaceId: string, customerId: string, token?: string): Promise<CustomerTag[]> {
  return apiRequest<CustomerTag[]>(`/customers/${customerId}/tags`, { headers: workspaceHeaders(workspaceId, token) });
}
export async function addCustomerTag(workspaceId: string, customerId: string, tagId: string, token?: string): Promise<CustomerTag> {
  return apiRequest<CustomerTag>(`/customers/${customerId}/tags/${tagId}`, { method: "POST", headers: workspaceHeaders(workspaceId, token) });
}
export async function fetchCustomerNotes(workspaceId: string, customerId: string, token?: string): Promise<CustomerNote[]> {
  return apiRequest<CustomerNote[]>(`/customers/${customerId}/notes`, { headers: workspaceHeaders(workspaceId, token) });
}
export async function addCustomerNote(workspaceId: string, customerId: string, note: string, token?: string): Promise<CustomerNote> {
  return apiRequest<CustomerNote>(`/customers/${customerId}/notes`, { method: "POST", headers: workspaceHeaders(workspaceId, token), body: JSON.stringify({ note }) });
}
export async function fetchCustomerAddresses(workspaceId: string, customerId: string, token?: string): Promise<CustomerAddress[]> {
  return apiRequest<CustomerAddress[]>(`/customers/${customerId}/addresses`, { headers: workspaceHeaders(workspaceId, token) });
}
export async function addCustomerAddress(workspaceId: string, customerId: string, payload: Partial<CustomerAddress>, token?: string): Promise<CustomerAddress> {
  return apiRequest<CustomerAddress>(`/customers/${customerId}/addresses`, { method: "POST", headers: workspaceHeaders(workspaceId, token), body: JSON.stringify(payload) });
}
export async function fetchAttachments(workspaceId: string, entityType: AttachmentEntityType, entityId: string, token?: string): Promise<Attachment[]> {
  return apiRequest<Attachment[]>(`/attachments?entity_type=${entityType}&entity_id=${entityId}`, { headers: workspaceHeaders(workspaceId, token) });
}
export async function addAttachment(workspaceId: string, payload: { entity_type: AttachmentEntityType; entity_id: string; file_url: string; file_name?: string }, token?: string): Promise<Attachment> {
  return apiRequest<Attachment>("/attachments", { method: "POST", headers: workspaceHeaders(workspaceId, token), body: JSON.stringify(payload) });
}
