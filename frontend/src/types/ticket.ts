import type { Order } from "./order";

export type TicketStatus =
  | "open"
  | "investigating"
  | "waiting_for_customer"
  | "waiting_for_approval"
  | "escalated"
  | "resolved"
  | "closed";

export type TicketPriority = "low" | "medium" | "high" | "urgent";

export type TicketIntent =
  | "late_delivery"
  | "damaged_item"
  | "wrong_item"
  | "refund_status"
  | "other";

export type SenderType = "customer" | "agent" | "ai";

export type TicketMessage = {
  id: string;
  sender_id: string | null;
  sender_type: SenderType;
  body: string;
  created_at: string;
};

export type TicketSummary = {
  id: string;
  user_id: string;
  order_id: string;
  assigned_agent_id: string | null;
  subject: string;
  status: TicketStatus;
  priority: TicketPriority;
  intent: TicketIntent | null;
  sla_due_at: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
};

export type TicketDetail = TicketSummary & {
  description: string;
  order: Order;
  messages: TicketMessage[];
};

export type TicketCreatePayload = {
  order_id: string;
  subject: string;
  description: string;
};

export type Attachment = {
  id: string;
  ticket_id: string;
  uploaded_by: string | null;
  file_name: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  download_url: string; // a temporary signed link
  download_url_expires_in: number; // seconds until the link stops working
};
