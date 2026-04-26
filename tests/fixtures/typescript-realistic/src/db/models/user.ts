// User database model.
import type { User } from "@/types";

export interface UserRow {
  id: string;
  email: string;
  name: string;
  role: string;
  password_hash: string;
  created_at: string;
  updated_at: string;
}

export function rowToUser(row: UserRow): User {
  return {
    id: row.id,
    email: row.email,
    name: row.name,
    role: row.role as User["role"],
    createdAt: new Date(row.created_at),
    updatedAt: new Date(row.updated_at),
  };
}

export function userToInsertParams(user: Omit<User, "id" | "createdAt" | "updatedAt">, passwordHash: string) {
  return {
    email: user.email,
    name: user.name,
    role: user.role,
    password_hash: passwordHash,
  };
}

export const USER_SELECT_COLUMNS = [
  "id",
  "email",
  "name",
  "role",
  "created_at",
  "updated_at",
].join(", ");
