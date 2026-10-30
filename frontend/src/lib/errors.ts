import axios from "axios";

export function getStatus(error: unknown): number | null {
  return axios.isAxiosError(error)
    ? error.response?.status ?? null
    : null;
}

export function isNetworkError(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response === undefined;
}

function serverDetail(error: unknown): string | null {
  if (!axios.isAxiosError(error)) return null;
  const data: unknown = error.response?.data;
  if (typeof data === "object" && data !== null && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return null;
}

/** Turns any error into a short message that is safe to show a customer. */
export function friendlyError(error: unknown): string {
  if (isNetworkError(error)) {
    return "We could not reach the server. Check your connection and try again.";
  }
  const status = getStatus(error);
  if (status === 401) return "Your session has ended. Please log in again.";
  if (status === 403) return "You do not have permission to do that.";
  if (status === 404) return "We could not find what you were looking for.";
  if (status === 413) return "That file is too large.";
  if (status === 422) return "Some of the information is not valid. Please check it and try again.";
  if (status === 429) return "Too many requests. Please wait a moment and try again.";
  if (status !== null && status >= 500) return "Something went wrong on our side. Please try again later.";
  const detail = serverDetail(error);
  if (detail) return detail;
  return "Something went wrong. Please try again.";
}
