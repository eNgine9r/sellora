export type LeadStatus = "NEW" | "IN_PROGRESS" | "QUALIFIED" | "CONVERTED" | "LOST";

export type LeadSource = {
  id: string;
  workspace_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Lead = {
  id: string;
  workspace_id: string;
  instagram_username: string | null;
  instagram_profile_url: string | null;
  name: string;
  phone: string | null;
  lead_source_id: string | null;
  campaign_id: string | null;
  campaign_name: string | null;
  status: LeadStatus;
  notes: string | null;
  assigned_user_id: string | null;
  expected_revenue: string | null;
  loss_reason: string | null;
  first_contact_at: string | null;
  last_contact_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Customer = {
  id: string;
  workspace_id: string;
  name: string;
  phone: string | null;
  instagram_username: string | null;
  city: string | null;
  region: string | null;
  total_orders: number;
  paid_orders: number;
  total_spent: string;
  unpriced_orders: number;
  last_order_at: string | null;
  last_order_number: string | null;
  last_order_status: string | null;
  last_order_payment_status: string | null;
  source: string;
  lifecycle_status: string;
  profile_status: string;
  source_direct_conversation_id: string | null;
  created_at: string;
  updated_at: string;
};
