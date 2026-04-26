// Order database model.
import type { Order, OrderItem } from "@/types";
import type { UserRow } from "@/db/models/user";

export interface OrderRow {
  id: string;
  user_id: string;
  status: string;
  total: string;
  created_at: string;
}

export interface OrderItemRow {
  order_id: string;
  product_id: string;
  quantity: number;
  unit_price: string;
}

export function rowToOrder(row: OrderRow, items: OrderItemRow[]): Order {
  return {
    id: row.id,
    userId: row.user_id,
    status: row.status as Order["status"],
    total: parseFloat(row.total),
    items: items.map(rowToOrderItem),
    createdAt: new Date(row.created_at),
  };
}

function rowToOrderItem(row: OrderItemRow): OrderItem {
  return {
    productId: row.product_id,
    quantity: row.quantity,
    unitPrice: parseFloat(row.unit_price),
  };
}

export function orderInsertParams(userId: string, total: number) {
  return { user_id: userId, total: total.toFixed(2), status: "pending" };
}

export type UserWithOrders = UserRow & { orders: Order[] };
