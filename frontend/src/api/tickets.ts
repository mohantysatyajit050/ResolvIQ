import type { Page } from "../types/common";
import type {
  TicketCreatePayload,
  TicketDetail,
  TicketMessage,
  TicketStatus,
  TicketSummary,
} from "../types/ticket";
import { apiClient } from "./client";

export type TicketListParams = {
  status?: TicketStatus;
  limit?: number;
  offset?: number;
};

export async function fetchTickets(
  params: TicketListParams = {},
): Promise<Page<TicketSummary>> {
  const response = await apiClient.get<Page<TicketSummary>>("/tickets", { params });
  return response.data;
}

export async function fetchTicket(ticketId: string): Promise<TicketDetail> {
  const response = await apiClient.get<TicketDetail>(`/tickets/${ticketId}`);
  return response.data;
}

export async function createTicket(
  payload: TicketCreatePayload,
): Promise<TicketDetail> {
  const response = await apiClient.post<TicketDetail>("/tickets", payload);
  return response.data;
}

export async function addMessage(
  ticketId: string,
  body: string,
): Promise<TicketMessage> {
  const response = await apiClient.post<TicketMessage>(
    `/tickets/${ticketId}/messages`,
    { body },
  );
  return response.data;
}
