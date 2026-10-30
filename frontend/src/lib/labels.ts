import type { OrderStatus } from "../types/order";
import type { TicketStatus } from "../types/ticket";

export const ORDER_STATUS_LABEL: Record<OrderStatus, string> = {
  placed: "Placed",
  shipped: "Shipped",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  cancelled: "Cancelled",
  returned: "Returned",
};

export const TICKET_STATUS_LABEL: Record<TicketStatus, string> = {
  open: "Open",
  investigating: "Investigating",
  waiting_for_customer: "Waiting for you",
  waiting_for_approval: "Waiting for approval",
  escalated: "Escalated",
  resolved: "Resolved",
  closed: "Closed",
};

/** One plain sentence telling the customer what a status means for them. */
export const TICKET_STATUS_HELP: Record<TicketStatus, string> = {
  open: "We received your complaint and will start looking into it soon.",
  investigating: "We are looking into your complaint.",
  waiting_for_customer: "We need more information from you. Please reply below.",
  waiting_for_approval: "Your case is waiting for an internal approval.",
  escalated: "Your case has been passed to a senior team member.",
  resolved: "We think this is fixed. If it is not, reply and we will reopen it.",
  closed: "This ticket is closed.",
};
