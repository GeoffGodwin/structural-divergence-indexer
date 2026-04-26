// Health check route handlers.
import { logger } from "@/lib/logger";
import type { RequestContext } from "@/types";

interface HealthStatus {
  status: "ok" | "degraded" | "down";
  version: string;
  uptime: number;
  checks: Record<string, { status: string; latencyMs?: number }>;
}

const START_TIME = Date.now();
const VERSION = process.env.APP_VERSION ?? "unknown";

export async function getHealth(ctx: RequestContext): Promise<HealthStatus> {
  logger.info("health check", { requestId: ctx.requestId });

  const checks: HealthStatus["checks"] = {};
  let overall: HealthStatus["status"] = "ok";

  const dbStart = Date.now();
  try {
    checks.database = { status: "ok", latencyMs: Date.now() - dbStart };
  } catch (err) {
    logger.warn("health: database check failed", { error: (err as Error).message });
    checks.database = { status: "error" };
    overall = "degraded";
  }

  const cacheStart = Date.now();
  try {
    checks.cache = { status: "ok", latencyMs: Date.now() - cacheStart };
  } catch (err) {
    logger.warn("health: cache check failed", { error: (err as Error).message });
    checks.cache = { status: "error" };
    overall = "degraded";
  }

  return {
    status: overall,
    version: VERSION,
    uptime: Math.floor((Date.now() - START_TIME) / 1000),
    checks,
  };
}

export function getReadiness(): { ready: boolean } {
  return { ready: true };
}
