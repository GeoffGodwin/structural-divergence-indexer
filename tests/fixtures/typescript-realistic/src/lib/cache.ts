// In-memory and Redis cache utilities.
import { config } from "@/config";

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

const localCache = new Map<string, CacheEntry<unknown>>();

export function cacheSet<T>(key: string, value: T, ttlMs = 60_000): void {
  localCache.set(key, { value, expiresAt: Date.now() + ttlMs });
}

export function cacheGet<T>(key: string): T | null {
  const entry = localCache.get(key) as CacheEntry<T> | undefined;
  if (!entry) return null;
  if (Date.now() > entry.expiresAt) {
    localCache.delete(key);
    return null;
  }
  return entry.value;
}

export function cacheDelete(key: string): void {
  localCache.delete(key);
}

export function cacheFlush(): void {
  localCache.clear();
}

export async function withCache<T>(
  key: string,
  ttlMs: number,
  fetcher: () => Promise<T>,
): Promise<T> {
  const cached = cacheGet<T>(key);
  if (cached !== null) return cached;

  const value = await fetcher();
  cacheSet(key, value, ttlMs);
  return value;
}

export function cacheStats(): { size: number; host: string } {
  return {
    size: localCache.size,
    host: config.redisHost,
  };
}
