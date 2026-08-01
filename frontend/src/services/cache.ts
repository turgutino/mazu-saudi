/**
 * Tiny sessionStorage-backed TTL cache for near-static reference data
 * (regions/hazards/models) so navigating between pages within the same
 * tab doesn't re-hit the backend on every mount. Falls back to always
 * calling `fetcher` if sessionStorage is unavailable (e.g. private mode)
 * or the cached payload fails to parse.
 */

const CACHE_PREFIX = 'mazu-cache:v1:';

export const ONE_HOUR_MS = 60 * 60 * 1000;

interface CacheEntry<T> {
  data: T;
  expiresAt: number;
}

function readCache<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(CACHE_PREFIX + key);
    if (!raw) return null;
    const entry: CacheEntry<T> = JSON.parse(raw);
    if (entry.expiresAt <= Date.now()) return null;
    return entry.data;
  } catch {
    return null;
  }
}

function writeCache<T>(key: string, data: T, ttlMs: number): void {
  try {
    const entry: CacheEntry<T> = { data, expiresAt: Date.now() + ttlMs };
    sessionStorage.setItem(CACHE_PREFIX + key, JSON.stringify(entry));
  } catch {
    // storage full/unavailable -- caching is a pure optimization, ignore.
  }
}

/**
 * Returns the cached value for `key` if still fresh; otherwise calls
 * `fetcher`, caches the result for `ttlMs`, and returns it.
 */
export async function withCache<T>(key: string, ttlMs: number, fetcher: () => Promise<T>): Promise<T> {
  const cached = readCache<T>(key);
  if (cached !== null) return cached;

  const data = await fetcher();
  writeCache(key, data, ttlMs);
  return data;
}

/** Clears one cached key (or everything cached by this module if omitted). */
export function clearCache(key?: string): void {
  try {
    if (key) {
      sessionStorage.removeItem(CACHE_PREFIX + key);
      return;
    }
    Object.keys(sessionStorage)
      .filter((k) => k.startsWith(CACHE_PREFIX))
      .forEach((k) => sessionStorage.removeItem(k));
  } catch {
    // ignore
  }
}
