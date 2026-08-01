import type { MonitorRegionData } from '@/mocks/monitor';
import {
  GenericCurrentReading,
  mapReading,
  transformHourlyToForecast,
  buildRegionData,
} from './weatherUtils';

// --- Open-Meteo API types ---

interface OpenMeteoCurrent extends GenericCurrentReading {
  cloud_cover: number;
}

interface OpenMeteoHourly {
  time: string[];
  temperature_2m: number[];
  precipitation: number[];
}

export interface OpenMeteoResponse {
  latitude: number;
  longitude: number;
  current: OpenMeteoCurrent;
  hourly: OpenMeteoHourly;
}

// --- Region configs ---

export interface WeatherRegionConfig {
  regionId: string;
  regionName: string;
  nameEn: string;
  lat: number;
  lon: number;
  mapX: number;
  mapY: number;
}

export const weatherRegions: WeatherRegionConfig[] = [
  { regionId: 'jazan', regionName: '吉赞', nameEn: 'Jazan', lat: 16.8892, lon: 42.5511, mapX: 38.9, mapY: 94.4 },
  { regionId: 'riyadh', regionName: '利雅得', nameEn: 'Riyadh', lat: 24.7136, lon: 46.6753, mapX: 57.6, mapY: 45.5 },
  { regionId: 'jeddah', regionName: '吉达', nameEn: 'Jeddah', lat: 21.5433, lon: 39.1728, mapX: 23.5, mapY: 65.4 },
  { regionId: 'makkah', regionName: '麦加', nameEn: 'Makkah', lat: 21.3891, lon: 39.8579, mapX: 26.6, mapY: 66.3 },
  { regionId: 'dammam', regionName: '达曼', nameEn: 'Dammam', lat: 26.4207, lon: 50.0888, mapX: 73.1, mapY: 34.9 },
  { regionId: 'abha', regionName: '艾卜哈', nameEn: 'Abha', lat: 18.2164, lon: 42.5053, mapX: 38.7, mapY: 86.1 },
  { regionId: 'medina', regionName: '麦地那', nameEn: 'Medina', lat: 24.5247, lon: 39.5692, mapX: 25.3, mapY: 46.7 },
  { regionId: 'tabuk', regionName: '塔布克', nameEn: 'Tabuk', lat: 28.3835, lon: 36.5771, mapX: 11.7, mapY: 22.6 },
];

const FORECAST_HOURS = 48;

// --- Main transformer ---

export function transformWeatherData(
  rawResponses: OpenMeteoResponse[],
): { regions: MonitorRegionData[]; summary: { totalRegions: number; activeAlerts: number; lastRefresh: string; nextRefresh: string } } {
  const now = new Date();
  const lastRefresh = now.toISOString().replace('T', ' ').slice(0, 16);
  const nextBucket = new Date(now);
  nextBucket.setUTCHours(Math.floor(now.getUTCHours() / 6) * 6 + 6, 0, 0, 0);
  const nextRefresh = nextBucket.toISOString().replace('T', ' ').slice(0, 16);

  const regions = rawResponses.map((raw) => {
    const cfg = weatherRegions.find((r) =>
      Math.abs(r.lat - raw.latitude) < 0.5 && Math.abs(r.lon - raw.longitude) < 0.5,
    );
    if (!cfg) {
      throw new Error(`Cannot match API response lat=${raw.latitude} lon=${raw.longitude} to any region`);
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
      nextRefresh,
    },
  };
}
