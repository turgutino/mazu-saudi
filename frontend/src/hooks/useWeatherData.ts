import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { MonitorRegionData } from '@/mocks/monitor';
import {
  transformWeatherData,
  type OpenMeteoResponse,
} from '@/services/weatherApi';
import { loadMonitorData } from '@/services/monitorSnapshotApi';

interface UseWeatherDataResult {
  regions: MonitorRegionData[];
  loading: boolean;
  error: string | null;
  lastRefresh: string;
  nextRefresh: string;
  isRealData: boolean;
  cacheHit: boolean;
  refresh: () => void;
}

export function useWeatherData(): UseWeatherDataResult {
  const { t } = useTranslation();
  const [regions, setRegions] = useState<MonitorRegionData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState('');
  const [nextRefresh, setNextRefresh] = useState('');
  const [isRealData, setIsRealData] = useState(false);
  const [cacheHit, setCacheHit] = useState(false);

  const inFlightRef = useRef(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async (forceRefresh = false) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const result = await loadMonitorData<OpenMeteoResponse[]>(
        'open-meteo',
        forceRefresh,
      );
      const { regions: data, summary } = transformWeatherData(result.data);
      setRegions(data);
      setLastRefresh(summary.lastRefresh);
      setNextRefresh(summary.nextRefresh);
      setIsRealData(true);
      setCacheHit(result.cacheHit);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('common.requestFailed');
      setError(msg);
      setRegions([]);
      setLastRefresh('');
      setNextRefresh('');
      setIsRealData(false);
      setCacheHit(false);
    } finally {
      setLoading(false);
      inFlightRef.current = false;
    }
  }, [t]);

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  useEffect(() => {
    // Check the database periodically; third-party data is fetched only when
    // the fixed UTC six-hour bucket has no snapshot.
    intervalRef.current = setInterval(() => loadData(false), 30 * 60 * 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loadData]);

  const refresh = useCallback(() => {
    loadData(true);
  }, [loadData]);

  return {
    regions,
    loading,
    error,
    lastRefresh,
    nextRefresh,
    isRealData,
    cacheHit,
    refresh,
  };
}
