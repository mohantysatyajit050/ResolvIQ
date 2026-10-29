import type { RegisterPayload, User } from "../types/auth";
import { apiClient } from "./client";

export async function loginRequest(email: string, password: string): Promise<void> {
  // The server answers by setting the session cookies. JavaScript stores nothing.
  await apiClient.post("/auth/login", { email, password });
}

export async function logoutRequest(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function registerRequest(payload: RegisterPayload): Promise<User> {
  const response = await apiClient.post<User>("/auth/register", payload);
  return response.data;
}

export async function fetchMe(): Promise<User> {
  const response = await apiClient.get<User>("/auth/me");
  return response.data;
}
