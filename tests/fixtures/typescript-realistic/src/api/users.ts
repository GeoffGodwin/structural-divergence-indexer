// User route handlers.
import { findUserById, findUserByEmail } from "@/db/queries";
import { logger } from "@/lib/logger";
import { validateUserInput, assertNoErrors } from "@/lib/validate";
import type { ApiResponse, User, RequestContext } from "@/types";

export async function getUser(
  ctx: RequestContext,
  userId: string,
): Promise<ApiResponse<User>> {
  logger.info("getUser", { requestId: ctx.requestId, userId });

  try {
    const user = await findUserById(userId);
    if (!user) {
      return { data: null, error: "User not found", status: 404 };
    }
    return { data: user, error: null, status: 200 };
  } catch (err) {
    logger.error("getUser failed", err instanceof Error ? err : undefined, { userId });
    return { data: null, error: "Internal server error", status: 500 };
  }
}

export async function getUserByEmail(
  ctx: RequestContext,
  email: string,
): Promise<ApiResponse<User>> {
  logger.info("getUserByEmail", { requestId: ctx.requestId, email });

  const errors = validateUserInput({ email });
  try {
    assertNoErrors(errors);
  } catch (err) {
    return { data: null, error: (err as Error).message, status: 422 };
  }

  try {
    const user = await findUserByEmail(email);
    if (!user) {
      return { data: null, error: "User not found", status: 404 };
    }
    return { data: user, error: null, status: 200 };
  } catch (err) {
    logger.error("getUserByEmail failed", err instanceof Error ? err : undefined);
    return { data: null, error: "Internal server error", status: 500 };
  }
}
