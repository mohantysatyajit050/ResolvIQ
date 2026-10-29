import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { fetchMe, loginRequest, logoutRequest, registerRequest } from "../api/auth";
import { setSessionActive, setUnauthorizedHandler } from "../api/client";
import { getStatus } from "../lib/errors";
import { hasSessionHint } from "../lib/session";
import type { RegisterPayload, User } from "../types/auth";
import { AuthContext } from "./auth-context";
import type { AuthContextValue, AuthStatus } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // If a session probably exists, we must ask the server who it belongs to, so we start "loading".
  const [status, setStatus] = useState<AuthStatus>(() =>
    hasSessionHint() ? "loading" : "anonymous",
  );

  const clearSession = useCallback(() => {
    setSessionActive(false);
    setUser(null);
    setStatus("anonymous");
  }, []);

  const logout = useCallback(() => {
    // Ask the server to delete the cookies. The screen does not wait for the answer.
    void logoutRequest().catch(() => undefined);
    clearSession();
  }, [clearSession]);

  // On first load, ask the server who the session belongs to. Never trust the screen alone.
  useEffect(() => {
    if (!hasSessionHint()) return;
    let cancelled = false;
    fetchMe()
      .then((me) => {
        if (cancelled) return;
        setSessionActive(true);
        setUser(me);
        setStatus("authenticated");
      })
      .catch((error: unknown) => {
        const code = getStatus(error);
        if (code === 401 || code === 403) {
          // expired, tampered with, or disabled: remove the leftover cookies
          void logoutRequest().catch(() => undefined);
        }
        if (cancelled) return;
        clearSession();
      });
    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  // Any API call that gets a 401 while logged in (for example an expired session) logs out.
  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const login = useCallback(
    async (email: string, password: string): Promise<User> => {
      await loginRequest(email, password); // the server sets the cookies
      try {
        const me = await fetchMe();
        setSessionActive(true);
        setUser(me);
        setStatus("authenticated");
        return me;
      } catch (error) {
        void logoutRequest().catch(() => undefined); // never leave a half-finished login behind
        throw error;
      }
    },
    [],
  );

  const register = useCallback(
    async (payload: RegisterPayload): Promise<User> => {
      await registerRequest(payload);
      return login(payload.email, payload.password);
    },
    [login],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, register, logout }),
    [user, status, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
