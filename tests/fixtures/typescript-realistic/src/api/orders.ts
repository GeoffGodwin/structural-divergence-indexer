// Order route handlers.
import { findOrdersByUser } from "@/db/queries";
import { logger } from "@/lib/logger";
import { NotFoundError, isAppError } from "@/lib/errors";
import type { ApiResponse, Order, RequestContext } from "@/types";

export async function getUserOrders(
  ctx: RequestContext,
  userId: string,
): Promise<ApiResponse<Order[]>> {
  logger.info("getUserOrders", { requestId: ctx.requestId, userId });

  try {
    const orders = await findOrdersByUser(userId);
    logger.info("getUserOrders success", { count: orders.length });
    return { data: orders, error: null, status: 200 };
  } catch (err) {
    if (isAppError(err)) {
      logger.warn("getUserOrders app error", { code: err.code });
      return { data: null, error: err.message, status: err.statusCode };
    }
    logger.error("getUserOrders failed", err instanceof Error ? err : undefined);
    return { data: null, error: "Internal server error", status: 500 };
  }
}

export async function getOrderById(
  ctx: RequestContext,
  orderId: string,
): Promise<ApiResponse<Order>> {
  logger.info("getOrderById", { requestId: ctx.requestId, orderId });

  try {
    const orders = await findOrdersByUser(ctx.userId ?? "");
    const order = orders.find((o) => o.id === orderId);
    if (!order) {
      throw new NotFoundError("Order", orderId);
    }
    return { data: order, error: null, status: 200 };
  } catch (err) {
    if (isAppError(err)) {
      return { data: null, error: err.message, status: err.statusCode };
    }
    logger.error("getOrderById failed", err instanceof Error ? err : undefined);
    return { data: null, error: "Internal server error", status: 500 };
  } finally {
    logger.info("getOrderById complete", { orderId });
  }
}
