import axios from "axios";

export function getStatus(error: unknown): number | null {
  return axios.isAxiosError(error)
    ? error.response?.status ?? null
    : null;
}

export function isNetworkError(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response === undefined;
}
