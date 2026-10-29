import type { UserRole } from "../types/auth";

/** Where each kind of user lands after logging in. */
export function homePathFor(role: UserRole): string {
  return role === "customer" ? "/orders" : "/agent/queue";
}
