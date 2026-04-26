// Application entrypoint: routes all incoming requests to handlers.
import { getUser, getUserByEmail } from "@/api/users";
import { getUserOrders, getOrderById } from "@/api/orders";
import { getProducts, searchProducts } from "@/api/products";
import { login, verifyToken } from "@/api/auth";
import { getHealth, getReadiness } from "@/api/health";
import { logger } from "@/lib/logger";
import { config } from "@/config";
import { ORDER_STATUSES } from "@/types";
import type { RequestContext } from "@/types";

function makeContext(requestId: string, userId?: string): RequestContext {
  return { requestId, userId, startTime: Date.now() };
}

function generateRequestId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export async function handleRequest(
  method: string,
  path: string,
  body: unknown,
  headers: Record<string, string>,
): Promise<{ status: number; body: unknown }> {
  const requestId = generateRequestId();
  const ctx = makeContext(requestId);

  logger.info("incoming request", { method, path, requestId });

  try {
    if (path === "/health") {
      const health = await getHealth(ctx);
      return { status: 200, body: health };
    }

    if (path === "/ready") {
      return { status: 200, body: getReadiness() };
    }

    if (method === "POST" && path === "/api/v1/auth/login") {
      const result = await login(ctx, body as Parameters<typeof login>[1]);
      return { status: result.status, body: result };
    }

    if (method === "GET" && path.startsWith("/api/v1/users/")) {
      const userId = path.split("/").pop() ?? "";
      const result = await getUser(ctx, userId);
      return { status: result.status, body: result };
    }

    if (method === "GET" && path.startsWith("/api/v1/orders/")) {
      const orderId = path.split("/").pop() ?? "";
      const result = await getOrderById(ctx, orderId);
      return { status: result.status, body: result };
    }

    if (method === "GET" && path === "/api/v1/products") {
      const result = await getProducts(ctx);
      return { status: result.status, body: result };
    }

    return { status: 404, body: { error: "Not found" } };
  } catch (err) {
    logger.error("unhandled error", err instanceof Error ? err : undefined, { path });
    return { status: 500, body: { error: "Internal server error" } };
  }
}

logger.info("Application starting", { port: config.port, env: config.nodeEnv });
