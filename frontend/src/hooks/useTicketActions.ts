import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadAttachment } from "../api/attachments";
import { addMessage, createTicket } from "../api/tickets";
import { queryKeys } from "../lib/queryKeys";
import type { TicketCreatePayload, TicketDetail } from "../types/ticket";

/** Uploads every file. Returns the names of the ones that failed. */
async function uploadAll(ticketId: string, files: File[]): Promise<string[]> {
  const results = await Promise.allSettled(
    files.map((file) => uploadAttachment(ticketId, file)),
  );
  const failed: string[] = [];
  results.forEach((result, index) => {
    const file = files[index];
    if (result.status === "rejected" && file) failed.push(file.name);
  });
  return failed;
}

type CreateComplaintInput = { payload: TicketCreatePayload; files: File[] };
type CreateComplaintResult = { ticket: TicketDetail; failedFiles: string[] };

export function useCreateComplaint() {
  const queryClient = useQueryClient();
  return useMutation<CreateComplaintResult, unknown, CreateComplaintInput>({
    mutationFn: async ({ payload, files }) => {
      const ticket = await createTicket(payload);
      // the ticket exists now, so a failed upload must not undo it
      const failedFiles = await uploadAll(ticket.id, files);
      return { ticket, failedFiles };
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.tickets.all });
    },
  });
}

export function useReply(ticketId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => addMessage(ticketId, body),
    onSettled: () => {
      // a reply can reopen a resolved ticket, so refresh the status too
      void queryClient.invalidateQueries({ queryKey: queryKeys.tickets.all });
    },
  });
}

export function useUploadFiles(ticketId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => uploadAll(ticketId, files),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.tickets.attachments(ticketId),
      });
    },
  });
}
