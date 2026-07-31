import { useState, useEffect, useCallback, useRef } from 'react';
import type { TomorrowIoEnhanced } from '@/services/tomorrowIoApi';
import {
  fetchAllRegionsTomorrowIo,
  extractEnhancedData,
  isTomorrowIoConfigured,
} from '@/services/tomorrowIoApi';

interface UseTomorrowIoDataResult {
  enhancedList: TomorrowIoEnhanced[] | null;
  loading: boolean;
  error: string | null;
  enabled: boolean;
  refresh: () => void;
}

export function useTomorrowIoData(): UseTomorrowIoDataResult {
  const enabled = isTomorrowIoConfigured();
  const [enhancedList, setEnhancedList] = useState<TomorrowIoEnhanced[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inFlightRef = useRef(false);

  const loadData = useCallback(async () => {
    if (!enabled || inFlightRef.current) return;
    inFlightRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const raw = await fetchAllRegionsTomorrowIo();
      const enhanced = extractEnhancedData(raw);
      setEnhancedList(enhanced);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Tomorrow.io 请求失败';
      setError(msg);
      setEnhancedList(null);
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
    enhancedList,
    loading,
    error,
    enabled,
    refresh,
  };
}