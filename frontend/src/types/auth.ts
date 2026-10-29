export type UserRole = "customer" | "agent" | "admin";

export type User = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone: string | null;
  is_active: boolean;
  created_at: string;
};

export type RegisterPayload = {
  name: string;
  email: string;
  password: string;
  phone?: string;
};
