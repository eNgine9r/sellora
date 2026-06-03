import { apiRequest } from "@/services/api";
import { Customer, Lead, LeadSource, LeadStatus } from "@/types/crm";

function workspaceHeaders(workspaceId?: string, token?: string): HeadersInit {
  return {
    ...(workspaceId ? { "X-Workspace-ID": workspaceId } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export type LeadFilters = {
  search?: string;
  status?: LeadStatus | "";
  leadSourceId?: string;
};

export type LeadCreatePayload = {
  instagram_username: string | null;
  instagram_profile_url: string | null;
  name: string;
  phone: string | null;
  lead_source_id: string | null;
  notes: string | null;
  assigned_user_id: string | null;
  expected_revenue: number | null;
  first_contact_at?: string | null;
  last_contact_at?: string | null;
};

export async function fetchLeadSources(workspaceId: string, token?: string): Promise<LeadSource[]> {
  return apiRequest<LeadSource[]>("/lead-sources", { headers: workspaceHeaders(workspaceId, token) });
}

export async function fetchLeads(workspaceId: string, filters: LeadFilters, token?: string): Promise<Lead[]> {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.status) params.set("status", filters.status);
  if (filters.leadSourceId) params.set("lead_source_id", filters.leadSourceId);
  const query = params.toString();
  return apiRequest<Lead[]>(`/leads${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId, token) });
}

export async function createLead(workspaceId: string, payload: LeadCreatePayload, token?: string): Promise<Lead> {
  return apiRequest<Lead>("/leads", {
    method: "POST",
    headers: workspaceHeaders(workspaceId, token),
    body: JSON.stringify(payload),
  });
}

export async function fetchCustomers(workspaceId: string, search?: string, token?: string): Promise<Customer[]> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  const query = params.toString();
  return apiRequest<Customer[]>(`/customers${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId, token) });
}

export type CustomerCreatePayload = {
  name: string;
  phone: string | null;
  instagram_username: string | null;
  city: string | null;
  region: string | null;
};

export async function createCustomer(workspaceId: string, payload: CustomerCreatePayload, token?: string): Promise<Customer> {
  return apiRequest<Customer>("/customers", {
    method: "POST",
    headers: workspaceHeaders(workspaceId, token),
    body: JSON.stringify(payload),
  });
}
