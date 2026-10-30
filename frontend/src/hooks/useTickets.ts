import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchAttachments } from "../api/attachments";
import { fetchTicket, fetchTickets } from "../api/tickets";
import type { TicketListParams } from "../api/tickets";
import { queryKeys } from "../lib/queryKeys";
import type { TicketStatus } from "../types/ticket";

// A customer cannot open a second ticket for an order while one of these is open.
// The server still has the final say (it answers 409), so this only guides the UI.
const ACTIVE_STATUSES: TicketStatus[] = [
  "open",
  "investigating",
  "waiting_for_customer",
  "waiting_for_approval",
  "escalated",
];

export function useTickets(params: TicketListParams) {
  return useQuery({
    queryKey: queryKeys.tickets.list(params),
    queryFn: () => fetchTickets(params),
    placeholderData: keepPreviousData,
  });
}

export function useTicket(ticketId: string) {
  return useQuery({
    queryKey: queryKeys.tickets.detail(ticketId),
    queryFn: () => fetchTicket(ticketId),
    enabled: ticketId !== "",
  });
}

export function useAttachments(ticketId: string) {
  return useQuery({
    queryKey: queryKeys.tickets.attachments(ticketId),
    queryFn: () => fetchAttachments(ticketId),
    enabled: ticketId !== "",
  });
}

/** Maps order id -> id of the ticket that is still active for that order. */
export function useActiveTicketByOrder() {
  return useQuery({
    queryKey: queryKeys.tickets.activeByOrder,
    queryFn: async () => {
      const page = await fetchTickets({ limit: 100 });
      const byOrder: Record<string, string> = {};
      for (const ticket of page.items) {
        if (ACTIVE_STATUSES.includes(ticket.status)) {
          byOrder[ticket.order_id] = ticket.id;
        }
      }
      return byOrder;
    },
  });
}
