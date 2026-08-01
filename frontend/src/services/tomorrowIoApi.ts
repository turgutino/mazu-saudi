import type { MonitorReading } from '@/mocks/monitor';

// --- Tomorrow.io Realtime API types ---

interface TomorrowIoRealtimeValues {
  temperature: number;
  windSpeed: number;
  windGust: number;
  fireIndex: number;
  thunderstormProbability: number;
  precipitationIntensity: number;
}

export interface TomorrowIoRealtimeResponse {
  data: {
    time: string;
    values: TomorrowIoRealtimeValues;
  };
}

// --- Types for enhanced readings ---

export interface TomorrowIoEnhanced {
  windGust: number;
  fireIndex: number;
  thunderstormProb: number;
}

// --- Extract enhanced fields from responses ---

export function extractEnhancedData(
  rawResponses: TomorrowIoRealtimeResponse[],
): (TomorrowIoEnhanced | null)[] {
  return rawResponses.map((raw) => {
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
