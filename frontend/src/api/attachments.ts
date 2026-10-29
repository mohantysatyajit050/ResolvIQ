import type { Attachment } from "../types/ticket";
import { apiClient } from "./client";

export async function fetchAttachments(ticketId: string): Promise<Attachment[]> {
  const response = await apiClient.get<Attachment[]>(
    `/tickets/${ticketId}/attachments`,
  );
  return response.data;
}

export async function uploadAttachment(
  ticketId: string,
  file: File,
): Promise<Attachment> {
  const form = new FormData(); // the browser sends this as multipart/form-data
  form.append("file", file);
  const response = await apiClient.post<Attachment>(
    `/tickets/${ticketId}/attachments`,
    form,
  );
  return response.data;
}
