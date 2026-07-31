import type { MonitorReading } from '@/mocks/monitor';
import { weatherRegions } from './weatherApi';

// --- Tomorrow.io Realtime API types ---

interface TomorrowIoRealtimeValues {
  temperature: number;
  windSpeed: number;
  windGust: number;
  fireIndex: number;
  thunderstormProbability: number;
  precipitationIntensity: number;
}

interface TomorrowIoRealtimeResponse {
  data: {
    time: string;
    values: TomorrowIoRealtimeValues;
  };
}

// --- Constants ---

const REALTIME_FIELDS = [
  'temperature',
  'windSpeed',
  'windGust',
  'fireIndex',
  'thunderstormProbability',
  'precipitationIntensity',
].join(',');

// --- Types for enhanced readings ---

export interface TomorrowIoEnhanced {
  windGust: number;
  fireIndex: number;
  thunderstormProb: number;
}

// --- Fetch single region ---

async function fetchSingleRegion(lat: number, lon: number): Promise<TomorrowIoRealtimeResponse> {
  const key = import.meta.env.VITE_PUBLIC_TOMORROW_IO_KEY;
  const url = `https://api.tomorrow.io/v4/weather/realtime?location=${lat},${lon}&units=metric&fields=${REALTIME_FIELDS}&apikey=${key}`;
  const res = await fetch(url, { method: 'GET', headers: { Accept: 'application/json' } });
  if (!res.ok) {
    throw new Error(`Tomorrow.io error for ${lat},${lon}: ${res.status}`);
  }
  return res.json() as Promise<TomorrowIoRealtimeResponse>;
}

// --- Fetch all regions ---

export async function fetchAllRegionsTomorrowIo(): Promise<TomorrowIoRealtimeResponse[]> {
  return Promise.all(weatherRegions.map((cfg) => fetchSingleRegion(cfg.lat, cfg.lon)));
}

// --- Extract enhanced fields from responses ---

export function extractEnhancedData(
  rawResponses: TomorrowIoRealtimeResponse[],
): (TomorrowIoEnhanced | null)[] {
  return rawResponses.map((raw, idx) => {
    const v = raw?.data?.values;
    if (!v) return null;
    return {
      windGust: Math.round(v.windGust * 10) / 10,
      fireIndex: Math.round(v.fireIndex),
      thunderstormProb: Math.round(v.thunderstormProbability),
    };
  });
}

// --- Merge enhanced into MonitorReading ---

export function mergeEnhancedIntoReading(
  base: MonitorReading,
  enhanced: TomorrowIoEnhanced | null,
): MonitorReading {
  return {
    ...base,
    windGust: enhanced?.windGust ?? 0,
    fireIndex: enhanced?.fireIndex ?? 0,
    thunderstormProb: enhanced?.thunderstormProb ?? 0,
  };
}

// --- Check if key is configured ---

export function isTomorrowIoConfigured(): boolean {
  return !!import.meta.env.VITE_PUBLIC_TOMORROW_IO_KEY;
}