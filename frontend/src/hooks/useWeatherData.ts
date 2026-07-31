import { useState, useEffect, useCallback, useRef } from 'react';
import type { MonitorRegionData } from '@/mocks/monitor';
import {
  fetchAllRegions,
  transformWeatherData,
  getOpenMeteoFallbackData,
} from '@/services/weatherApi';

interface UseWeatherDataResult {
  regions: MonitorRegionData[];
  loading: boolean;
  error: string | null;
  lastRefresh: string;
  nextRefresh: string;
  isRealData: boolean;
  refresh: () => void;
}

export function useWeatherData(): UseWeatherDataResult {
  const [regions, setRegions] = useState<MonitorRegionData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState('');
  const [nextRefresh, setNextRefresh] = useState('');
  const [isRealData, setIsRealData] = useState(false);

  const inFlightRef = useRef(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const raw = await fetchAllRegions();
      const { regions: data, summary } = transformWeatherData(raw);
      setRegions(data);
      setLastRefresh(summary.lastRefresh);
      setNextRefresh(summary.nextRefresh);
      setIsRealData(true);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求失败';
      setError(msg);
      const fallback = getOpenMeteoFallbackData();
      setRegions(fallback.regions);
      setLastRefresh(fallback.summary.lastRefresh);
      setNextRefresh(fallback.summary.nextRefresh);
      setIsRealData(false);
    } finally {
      setLoading(false);
      inFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    intervalRef.current = setInterval(loadData, 30 * 60 * 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loadData]);

  const refresh = useCallback(() => {
    loadData();
  }, [loadData]);

  return {
    regions,
    loading,
    error,
    lastRefresh,
    nextRefresh,
    isRealData,
    refresh,
  };
}