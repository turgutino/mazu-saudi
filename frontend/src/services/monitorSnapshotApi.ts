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

interface MonitorSourceStatus {
  source: MonitorSource;
  configured: boolean;
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

async function refreshSnapshot<T>(source: MonitorSource): Promise<MonitorSnapshot<T>> {
  const response = await fetch(`${API_BASE}/monitor/snapshots/${encodeURIComponent(source)}/refresh`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`后端监测采集失败 (${response.status}): ${detail}`);
  }
  return response.json() as Promise<MonitorSnapshot<T>>;
}

export async function getMonitorSourceStatus(source: MonitorSource): Promise<boolean> {
  const response = await fetch(`${API_BASE}/monitor/sources`, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`监测数据源状态读取失败 (${response.status})`);
  const statuses = await response.json() as MonitorSourceStatus[];
  return statuses.find((status) => status.source === source)?.configured ?? false;
}

export async function loadMonitorData<T>(
  source: MonitorSource,
  forceRefresh = false,
): Promise<{ data: T; cacheHit: boolean; fetchedAt: string }> {
  if (!forceRefresh) {
    const cached = await getCurrentSnapshot<T>(source);
    if (cached) {
      return { data: cached.data, cacheHit: true, fetchedAt: cached.fetchedAt };
    }
  }

  const refreshed = await refreshSnapshot<T>(source);
  return { data: refreshed.data, cacheHit: false, fetchedAt: refreshed.fetchedAt };
}
