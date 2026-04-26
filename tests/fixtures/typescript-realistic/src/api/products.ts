// Product route handlers.
import { listProducts } from "@/db/queries";
import { logger } from "@/lib/logger";
import type { ApiResponse, Product, PaginatedResult, RequestContext } from "@/types";

export async function getProducts(
  ctx: RequestContext,
  page = 1,
  pageSize = 20,
): Promise<ApiResponse<PaginatedResult<Product>>> {
  logger.info("getProducts", { requestId: ctx.requestId, page, pageSize });

  try {
    const result = await listProducts(page, pageSize);
    return { data: result, error: null, status: 200 };
  } catch (err) {
    logger.error("getProducts failed", err instanceof Error ? err : undefined);
    return { data: null, error: "Internal server error", status: 500 };
  }
}

export async function searchProducts(
  ctx: RequestContext,
  query: string,
): Promise<ApiResponse<Product[]>> {
  logger.info("searchProducts", { requestId: ctx.requestId, query });

  if (!query || query.trim().length < 2) {
    return { data: null, error: "Query too short", status: 400 };
  }

  try {
    const all = await listProducts(1, 100);
    const filtered = all.items.filter(
      (p) =>
        p.name.toLowerCase().includes(query.toLowerCase()) ||
        p.description.toLowerCase().includes(query.toLowerCase()),
    );
    logger.info("searchProducts result", { count: filtered.length });
    return { data: filtered, error: null, status: 200 };
  } catch (err) {
    logger.error("searchProducts failed", err instanceof Error ? err : undefined);
    return { data: null, error: "Internal server error", status: 500 };
  }
}
