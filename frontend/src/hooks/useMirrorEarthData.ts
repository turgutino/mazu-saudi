import { useState, useEffect, useCallback, useRef } from 'react';
import type { MonitorRegionData } from '@/mocks/monitor';
import {
  transformMirrorEarthData,
  type MirrorEarthResponse,
} from '@/services/mirrorEarthApi';
import { getMonitorSourceStatus, loadMonitorData } from '@/services/monitorSnapshotApi';

interface UseMirrorEarthDataResult {
  regions: MonitorRegionData[] | null;
  loading: boolean;
  error: string | null;
  lastRefresh: string;
  enabled: boolean;
  refresh: () => void;
}

export function useMirrorEarthData(): UseMirrorEarthDataResult {
  const [enabled, setEnabled] = useState(false);
  const [regions, setRegions] = useState<MonitorRegionData[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState('');

  const inFlightRef = useRef(false);

  const loadData = useCallback(async (forceRefresh = false) => {
    if (!enabled || inFlightRef.current) return;
    inFlightRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const result = await loadMonitorData<MirrorEarthResponse[]>(
        'mirror-earth-cma',
        forceRefresh,
      );
      const { regions: data, summary } = transformMirrorEarthData(result.data);
      setRegions(data);
      setLastRefresh(summary.lastRefresh);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'CMA 请求失败';
      setError(msg);
      setRegions(null);
    } finally {
      setLoading(false);
      inFlightRef.current = false;
    }
  }, [enabled]);

  useEffect(() => {
    getMonitorSourceStatus('mirror-earth-cma')
      .then(setEnabled)
      .catch(() => setEnabled(false));
  }, []);

  useEffect(() => { if (enabled) loadData(false); }, [enabled, loadData]);

  const refresh = useCallback(() => {
    loadData(true);
  }, [loadData]);

  return {
    regions,
    loading,
    error,
    lastRefresh,
    enabled,
    refresh,
  };
}
