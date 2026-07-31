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

interface MirrorEarthResponse {
  latitude: number;
  longitude: number;
  current: MirrorEarthCurrent;
  hourly: MirrorEarthHourly;
}

// --- Constants ---

const FORECAST_HOURS = 48;

const HOURLY_VARS = 'temperature_2m,precipitation,cape,wind_speed_10m,wind_direction_10m,relative_humidity_2m,surface_pressure,visibility';

function getApiKey(): string {
  const key = import.meta.env.VITE_PUBLIC_MIRROR_EARTH_KEY;
  if (!key) {
    throw new Error('VITE_PUBLIC_MIRROR_EARTH_KEY is not configured');
  }
  return key;
}

// --- Fetch from Mirror Earth ---

async function fetchSingleRegion(cfg: {
  regionId: string;
  regionName: string;
  lat: number;
  lon: number;
}): Promise<MirrorEarthResponse> {
  const apikey = getApiKey();
  const url = `https://api.mirror-earth.com/v1/forecast?latitude=${cfg.lat}&longitude=${cfg.lon}&models=cma&hourly=${HOURLY_VARS}&forecast_days=2&temporal_resolution=hourly_1&timezone=UTC&apikey=${apikey}`;
  const res = await fetch(url, { method: 'GET', headers: { Accept: 'application/json' } });
  if (!res.ok) {
    throw new Error(`Mirror Earth error for ${cfg.regionName}: ${res.status}`);
  }
  return res.json() as Promise<MirrorEarthResponse>;
}

export async function fetchAllRegionsCma(): Promise<MirrorEarthResponse[]> {
  return Promise.all(weatherRegions.map((cfg) => fetchSingleRegion(cfg)));
}

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

// --- Check if key is configured ---

export function isMirrorEarthConfigured(): boolean {
  return !!import.meta.env.VITE_PUBLIC_MIRROR_EARTH_KEY;
}