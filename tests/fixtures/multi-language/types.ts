/**
 * Shared TypeScript type definitions for multi-language fixture.
 * Known imports: none
 * Known symbols: RequestOptions, AuthToken
 */

export interface RequestOptions {
  headers?: Record<string, string>;
  timeout?: number;
}

export type AuthToken = {
  token: string;
  expiresAt: number;
};
