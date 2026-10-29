import axios from "axios";
import { getCsrfToken } from "../lib/session";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 10_000,
  withCredentials: true, // send the httpOnly session cookie with every request
});

const SAFE_METHODS = new Set(["get", "head", "options"]);

let sessionActive = false;
let onUnauthorized: (() => void) | null = null;

/** The auth provider tells us whether someone is logged in right now. */
export function setSessionActive(active: boolean): void {
  sessionActive = active;
}

/** The auth provider registers a function here that logs the user out. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

// Every request that changes data carries the CSRF token as a header.
apiClient.interceptors.request.use((config) => {
  const method = (config.method ?? "get").toLowerCase();
  if (!SAFE_METHODS.has(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      config.headers.set("X-CSRF-Token", csrf);
    }
  }
  return config;
});

// A 401 while someone is logged in means the session ended (for example it expired).
// A 401 from the login call itself only means "wrong password", so it is ignored here.
apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const isLoginCall = error.config?.url === "/auth/login";
      if (!isLoginCall && sessionActive) {
        sessionActive = false;
        onUnauthorized?.();
      }
    }
    return Promise.reject(error);
  },
);
