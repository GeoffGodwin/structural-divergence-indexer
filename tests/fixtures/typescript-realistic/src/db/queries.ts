// Database query functions using parameterized SQL.
import { rowToUser, USER_SELECT_COLUMNS } from "@/db/models/user";
import { rowToOrder, rowToProduct } from "@/db/models/order";
import { PRODUCT_SELECT_COLUMNS } from "@/db/models/product";
import type { User, Order, Product, PaginatedResult } from "@/types";

// Minimal pool interface — real implementation uses pg or similar.
interface QueryResult<T = Record<string, unknown>> {
  rows: T[];
  rowCount: number;
}

declare function query<T>(sql: string, params?: unknown[]): Promise<QueryResult<T>>;

export async function findUserById(id: string): Promise<User | null> {
  const result = await query<ReturnType<typeof import("@/db/models/user").rowToUser>>(
    `SELECT ${USER_SELECT_COLUMNS} FROM users WHERE id = $1`,
    [id],
  );
  if (result.rowCount === 0) return null;
  return rowToUser(result.rows[0] as Parameters<typeof rowToUser>[0]);
}

export async function findUserByEmail(email: string): Promise<User | null> {
  const result = await query(
    `SELECT ${USER_SELECT_COLUMNS} FROM users WHERE email = $1`,
    [email],
  );
  if (result.rowCount === 0) return null;
  return rowToUser(result.rows[0] as Parameters<typeof rowToUser>[0]);
}

export async function listProducts(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResult<Product>> {
  const offset = (page - 1) * pageSize;
  const result = await query(
    `SELECT ${PRODUCT_SELECT_COLUMNS} FROM products LIMIT $1 OFFSET $2`,
    [pageSize, offset],
  );
  const total = await query("SELECT COUNT(*) FROM products");
  return {
    items: result.rows.map((r) => rowToProduct(r as Parameters<typeof rowToProduct>[0])),
    total: parseInt((total.rows[0] as { count: string }).count, 10),
    page,
    pageSize,
  };
}

export async function findOrdersByUser(userId: string): Promise<Order[]> {
  const result = await query(
    "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC",
    [userId],
  );
  return result.rows.map((r) => rowToOrder(r as Parameters<typeof rowToOrder>[0], []));
}
