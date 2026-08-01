import { useState, useEffect, useCallback, useRef } from 'react';
import type { TomorrowIoEnhanced } from '@/services/tomorrowIoApi';
import {
  extractEnhancedData,
  type TomorrowIoRealtimeResponse,
} from '@/services/tomorrowIoApi';
import { getMonitorSourceStatus, loadMonitorData } from '@/services/monitorSnapshotApi';

interface UseTomorrowIoDataResult {
  enhancedList: TomorrowIoEnhanced[] | null;
  loading: boolean;
  error: string | null;
  enabled: boolean;
  refresh: () => void;
}

export function useTomorrowIoData(): UseTomorrowIoDataResult {
  const [enabled, setEnabled] = useState(false);
  const [enhancedList, setEnhancedList] = useState<TomorrowIoEnhanced[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inFlightRef = useRef(false);

  const loadData = useCallback(async (forceRefresh = false) => {
    if (!enabled || inFlightRef.current) return;
    inFlightRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const result = await loadMonitorData<TomorrowIoRealtimeResponse[]>(
        'tomorrow-io',
        forceRefresh,
      );
      const enhanced = extractEnhancedData(result.data);
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
    getMonitorSourceStatus('tomorrow-io')
      .then(setEnabled)
      .catch(() => setEnabled(false));
  }, []);

  useEffect(() => { if (enabled) loadData(false); }, [enabled, loadData]);

  const refresh = useCallback(() => {
    loadData(true);
  }, [loadData]);

  return {
    enhancedList,
    loading,
    error,
    enabled,
    refresh,
  };
}
