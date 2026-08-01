import type { MonitorRegionData } from '@/mocks/monitor';
import {
  GenericCurrentReading,
  mapReading,
  transformHourlyToForecast,
  buildRegionData,
} from './weatherUtils';
import { weatherRegions } from './weatherApi';

// --- Mirror Earth API types ---

type MirrorEarthCurrent = GenericCurrentReading;

interface MirrorEarthHourly {
  time: string[];
  temperature_2m: number[];
  precipitation: number[];
}

export interface MirrorEarthResponse {
  latitude: number;
  longitude: number;
  current: MirrorEarthCurrent;
  hourly: MirrorEarthHourly;
}

// --- Constants ---

const FORECAST_HOURS = 48;


// --- Main transformer ---

export function transformMirrorEarthData(
  rawResponses: MirrorEarthResponse[],
): { regions: MonitorRegionData[]; summary: { totalRegions: number; activeAlerts: number; lastRefresh: string } } {
  const now = new Date();
  const lastRefresh = now.toISOString().replace('T', ' ').slice(0, 16);

  const regions = rawResponses.map((raw) => {
    const cfg = weatherRegions.find((r) =>
      Math.abs(r.lat - raw.latitude) < 0.5 && Math.abs(r.lon - raw.longitude) < 0.5,
    );
    if (!cfg) {
      throw new Error(`Cannot match Mirror Earth response lat=${raw.latitude} lon=${raw.longitude} to any region`);
    }

    const readings = mapReading(raw.current);
    const forecast = transformHourlyToForecast(raw.hourly, FORECAST_HOURS);

    return buildRegionData(
      cfg.regionId,
      cfg.regionName,
      cfg.nameEn,
      cfg.lat,
      cfg.lon,
      cfg.mapX,
      cfg.mapY,
      readings,
      forecast,
      lastRefresh,
    );
  });

  const activeAlerts = regions.reduce((sum, r) => sum + r.activeAlertCount, 0);

  return {
    regions,
    summary: {
      totalRegions: regions.length,
      activeAlerts,
      lastRefresh,
    },
  };
}
