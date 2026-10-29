import { QueryClient } from "@tanstack/react-query";
import { getStatus } from "./errors";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Retry network hiccups, but never retry answers like 401, 403 or 404:
      // asking again would give the same answer.
      retry: (failureCount, error) => {
        const code = getStatus(error);
        if (code !== null && code >= 400 && code < 500) return false;
        return failureCount < 2;
      },
    },
  },
});
