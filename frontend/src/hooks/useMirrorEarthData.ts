import { useState, useEffect, useCallback, useRef } from 'react';
import type { MonitorRegionData } from '@/mocks/monitor';
import {
  fetchAllRegionsCma,
  transformMirrorEarthData,
  isMirrorEarthConfigured,
} from '@/services/mirrorEarthApi';
import { generateFallbackForecast } from '@/services/weatherUtils';
import { monitorRegions as fallbackRegions } from '@/mocks/monitor';
import { loadMonitorData } from '@/services/monitorSnapshotApi';

interface UseMirrorEarthDataResult {
  regions: MonitorRegionData[] | null;
  loading: boolean;
  error: string | null;
  lastRefresh: string;
  enabled: boolean;
  refresh: () => void;
}

function getFallbackCmaData(): MonitorRegionData[] {
  return fallbackRegions.map((r) => ({
    ...r,
    forecast: generateFallbackForecast(r.readings.temperature + 1.5, r.regionId, 48),
  }));
}

export function useMirrorEarthData(): UseMirrorEarthDataResult {
  const enabled = isMirrorEarthConfigured();
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
      const result = await loadMonitorData(
        'mirror-earth-cma',
        async () => transformMirrorEarthData(await fetchAllRegionsCma()),
        forceRefresh,
      );
      const { regions: data, summary } = result.data;
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
    if (enabled) {
      loadData(false);
    }
  }, [enabled, loadData]);

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
