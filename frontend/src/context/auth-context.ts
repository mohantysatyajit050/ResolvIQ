import { createContext } from "react";
import type { RegisterPayload, User } from "../types/auth";

export type AuthStatus = "loading" | "authenticated" | "anonymous";

export type AuthContextValue = {
  user: User | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
