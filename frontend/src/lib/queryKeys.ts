import type { TicketListParams } from "../api/tickets";

export const queryKeys = {
  orders: {
    all: ["orders"] as const,
    list: (limit: number, offset: number) => ["orders", "list", limit, offset] as const,
  },
  tickets: {
    all: ["tickets"] as const,
    list: (params: TicketListParams) => ["tickets", "list", params] as const,
    activeByOrder: ["tickets", "active-by-order"] as const,
    detail: (ticketId: string) => ["tickets", "detail", ticketId] as const,
    attachments: (ticketId: string) => ["tickets", "attachments", ticketId] as const,
  },
};
