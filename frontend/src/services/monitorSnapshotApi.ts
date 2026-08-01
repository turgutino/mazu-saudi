export type MonitorSource = 'open-meteo' | 'mirror-earth-cma' | 'tomorrow-io';

interface MonitorSnapshot<T> {
  snapshotId: string;
  source: MonitorSource;
  bucketStart: string;
  fetchedAt: string;
  expiresAt: string;
  cacheHit: boolean;
  data: T;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

async function getCurrentSnapshot<T>(source: MonitorSource): Promise<MonitorSnapshot<T> | null> {
  const response = await fetch(`${API_BASE}/monitor/snapshots/${encodeURIComponent(source)}`, {
    headers: { Accept: 'application/json' },
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`监测缓存读取失败 (${response.status})`);
  return response.json() as Promise<MonitorSnapshot<T>>;
}

async function saveSnapshot<T>(source: MonitorSource, data: T): Promise<MonitorSnapshot<T>> {
  const response = await fetch(`${API_BASE}/monitor/snapshots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ source, data }),
  });
  if (!response.ok) throw new Error(`监测缓存保存失败 (${response.status})`);
  return response.json() as Promise<MonitorSnapshot<T>>;
}

export async function loadMonitorData<T>(
  source: MonitorSource,
  fetchFromSource: () => Promise<T>,
  forceRefresh = false,
): Promise<{ data: T; cacheHit: boolean; fetchedAt: string }> {
  if (!forceRefresh) {
    try {
      const cached = await getCurrentSnapshot<T>(source);
      if (cached) {
        return { data: cached.data, cacheHit: true, fetchedAt: cached.fetchedAt };
      }
    } catch {
      // The monitoring page remains usable if the cache service is temporarily down.
    }
  }

  const data = await fetchFromSource();
  try {
    const saved = await saveSnapshot(source, data);
    return { data, cacheHit: false, fetchedAt: saved.fetchedAt };
  } catch {
    return { data, cacheHit: false, fetchedAt: new Date().toISOString() };
  }
}
