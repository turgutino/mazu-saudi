import { useState, useEffect, useCallback, useRef } from 'react';
import type { MonitorRegionData } from '@/mocks/monitor';
import {
  fetchAllRegionsCma,
  transformMirrorEarthData,
  isMirrorEarthConfigured,
} from '@/services/mirrorEarthApi';
import { generateFallbackForecast } from '@/services/weatherUtils';
import { monitorRegions as fallbackRegions } from '@/mocks/monitor';

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

  const loadData = useCallback(async () => {
    if (!enabled || inFlightRef.current) return;
    inFlightRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const raw = await fetchAllRegionsCma();
      const { regions: data, summary } = transformMirrorEarthData(raw);
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
      loadData();
    }
  }, [enabled, loadData]);

  const refresh = useCallback(() => {
    loadData();
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