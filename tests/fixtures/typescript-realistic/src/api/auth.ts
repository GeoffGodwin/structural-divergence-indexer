// Auth route handlers: login, logout, token verification.
import { findUserByEmail } from "@/db/queries";
import { logger } from "@/lib/logger";
import { validateUserInput, assertNoErrors } from "@/lib/validate";
import { UnauthorizedError, isAppError } from "@/lib/errors";
import type { ApiResponse, User, RequestContext } from "@/types";

interface LoginPayload {
  email: string;
  password: string;
}

interface AuthToken {
  token: string;
  expiresAt: number;
  user: User;
}

function generateToken(userId: string): string {
  return Buffer.from(`${userId}:${Date.now()}`).toString("base64");
}

export async function login(
  ctx: RequestContext,
  payload: LoginPayload,
): Promise<ApiResponse<AuthToken>> {
  logger.info("login attempt", { requestId: ctx.requestId, email: payload.email });

  const errors = validateUserInput({ email: payload.email });
  try {
    assertNoErrors(errors);
  } catch (validationErr) {
    return { data: null, error: (validationErr as Error).message, status: 422 };
  }

  try {
    const user = await findUserByEmail(payload.email);
    if (!user) {
      throw new UnauthorizedError("Invalid credentials");
    }
    const token = generateToken(user.id);
    logger.info("login success", { userId: user.id });
    return {
      data: { token, expiresAt: Date.now() + 3600_000, user },
      error: null,
      status: 200,
    };
  } catch (err) {
    if (isAppError(err)) {
      logger.warn("login rejected", { reason: err.message });
      return { data: null, error: err.message, status: err.statusCode };
    }
    logger.error("login failed", err instanceof Error ? err : undefined);
    return { data: null, error: "Internal server error", status: 500 };
  }
}

export async function verifyToken(
  ctx: RequestContext,
  token: string,
): Promise<ApiResponse<{ userId: string; valid: boolean }>> {
  logger.info("verifyToken", { requestId: ctx.requestId });

  try {
    const decoded = Buffer.from(token, "base64").toString("utf-8");
    const [userId] = decoded.split(":");
    if (!userId) {
      return { data: { userId: "", valid: false }, error: null, status: 200 };
    }
    return { data: { userId, valid: true }, error: null, status: 200 };
  } catch (err) {
    logger.error("verifyToken error", err instanceof Error ? err : undefined);
    return { data: null, error: "Invalid token", status: 401 };
  }
}
