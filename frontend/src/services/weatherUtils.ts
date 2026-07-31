import type {
  MonitorReading,
  HazardMonitorStatus,
  ForecastPoint,
  MonitorRegionData,
} from '@/mocks/monitor';
import { monitorRegions as fallbackRegions } from '@/mocks/monitor';

// --- Thresholds for hazard assessment ---

export const THRESHOLDS = {
  heat: { yellow: 40, orange: 45, red: 48 },
  cape: { yellow: 800, orange: 1500, red: 2200 },
  wind: { yellow: 14, orange: 18, red: 22 },
  precipitation: { yellow: 5, orange: 15, red: 30 },
  humidity: { high: 65, medium: 45 },
  visibility: { low: 5000, veryLow: 2000 },
};

// --- Generic current reading interface (shared by Open-Meteo & Mirror Earth) ---

export interface GenericCurrentReading {
  time: string;
  temperature_2m: number;
  relative_humidity_2m: number;
  wind_speed_10m: number;
  wind_direction_10m: number;
  surface_pressure: number;
  cape: number | null;
  precipitation: number;
  cloud_cover: number;
  visibility: number | null;
}

// --- Map raw current reading to MonitorReading ---

export function mapReading(c: GenericCurrentReading): MonitorReading {
  return {
    temperature: Math.round(c.temperature_2m),
    humidity: Math.round(c.relative_humidity_2m),
    windSpeed: Math.round(c.wind_speed_10m),
    windDir: Math.round(c.wind_direction_10m),
    pressure: Math.round(c.surface_pressure),
    cape: c.cape != null ? Math.round(c.cape) : 0,
    pw: Math.round(c.precipitation * 10 + c.relative_humidity_2m * 0.4),
    visibility: c.visibility != null ? Math.round(c.visibility / 1000) : 10,
    windGust: 0,
    fireIndex: 0,
    thunderstormProb: 0,
  };
}

// --- Hazard assessment engine ---

export function assessHazards(r: MonitorReading, regionId: string): HazardMonitorStatus[] {
  const hazards: HazardMonitorStatus[] = [];

  // 1. 极端高温
  let heatRisk: HazardMonitorStatus['riskLevel'] = 'green';
  let heatProb = 0.05;
  let heatTrend: HazardMonitorStatus['trend'] = 'stable';
  if (r.temperature >= THRESHOLDS.heat.red) {
    heatRisk = 'red';
    heatProb = 0.92;
    heatTrend = 'rising';
  } else if (r.temperature >= THRESHOLDS.heat.orange) {
    heatRisk = 'orange';
    heatProb = 0.72;
    heatTrend = 'rising';
  } else if (r.temperature >= THRESHOLDS.heat.yellow) {
    heatRisk = 'yellow';
    heatProb = 0.45;
    heatTrend = 'rising';
  }
  hazards.push({ hazardId: 'extreme-heat', hazardName: '极端高温', riskLevel: heatRisk, probability: heatProb, trend: heatTrend });

  // 2. 暴雨
  let rainRisk: HazardMonitorStatus['riskLevel'] = 'green';
  let rainProb = 0.05;
  let rainTrend: HazardMonitorStatus['trend'] = 'stable';
  const rainScore = (r.precipitation / 30) * 0.3 + (r.humidity / 100) * 0.35 + (r.cape / 2500) * 0.35;
  if (r.precipitation >= THRESHOLDS.precipitation.red || rainScore >= 0.85) {
    rainRisk = 'red';
    rainProb = 0.88;
    rainTrend = 'rising';
  } else if (r.precipitation >= THRESHOLDS.precipitation.orange || rainScore >= 0.65) {
    rainRisk = 'orange';
    rainProb = 0.65;
    rainTrend = 'rising';
  } else if (r.precipitation >= THRESHOLDS.precipitation.yellow || rainScore >= 0.45) {
    rainRisk = 'yellow';
    rainProb = 0.42;
    rainTrend = r.precipitation > 2 ? 'rising' : 'stable';
  }
  hazards.push({ hazardId: 'heavy-rain', hazardName: '暴雨', riskLevel: rainRisk, probability: rainProb, trend: rainTrend });

  // 3. 山洪 (flash flood)
  const floodSensitive = ['jazan', 'jeddah', 'makkah', 'abha'];
  const floodBoost = floodSensitive.includes(regionId) ? 0.15 : 0;
  let floodRisk: HazardMonitorStatus['riskLevel'] = 'green';
  let floodProb = 0.03;
  let floodTrend: HazardMonitorStatus['trend'] = 'stable';
  const floodScore = (r.precipitation / 25) * 0.4 + (r.humidity / 100) * 0.3 + (r.cape / 2000) * 0.3 + floodBoost;
  if (floodScore >= 0.85 || (r.precipitation >= 20 && floodSensitive.includes(regionId))) {
    floodRisk = 'red';
    floodProb = 0.90;
    floodTrend = 'rising';
  } else if (floodScore >= 0.65 || (r.precipitation >= 10 && floodSensitive.includes(regionId))) {
    floodRisk = 'orange';
    floodProb = 0.68;
    floodTrend = 'rising';
  } else if (floodScore >= 0.45 || (r.precipitation >= 5 && floodSensitive.includes(regionId))) {
    floodRisk = 'yellow';
    floodProb = 0.38;
    floodTrend = r.precipitation > 1 ? 'rising' : 'stable';
  }
  hazards.push({ hazardId: 'flash-flood', hazardName: '山洪', riskLevel: floodRisk, probability: floodProb, trend: floodTrend });

  // 4. 强对流
  let convRisk: HazardMonitorStatus['riskLevel'] = 'green';
  let convProb = 0.04;
  let convTrend: HazardMonitorStatus['trend'] = 'stable';
  const convScore = (r.cape / 2500) * 0.55 + (r.humidity / 100) * 0.25 + (r.precipitation / 20) * 0.2;
  if (r.cape >= THRESHOLDS.cape.red || convScore >= 0.90) {
    convRisk = 'red';
    convProb = 0.85;
    convTrend = 'rising';
  } else if (r.cape >= THRESHOLDS.cape.orange || convScore >= 0.70) {
    convRisk = 'orange';
    convProb = 0.62;
    convTrend = 'rising';
  } else if (r.cape >= THRESHOLDS.cape.yellow || convScore >= 0.50) {
    convRisk = 'yellow';
    convProb = 0.35;
    convTrend = 'rising';
  }
  hazards.push({ hazardId: 'severe-convection', hazardName: '强对流', riskLevel: convRisk, probability: convProb, trend: convTrend });

  // 5. 沙尘暴
  let dustRisk: HazardMonitorStatus['riskLevel'] = 'green';
  let dustProb = 0.04;
  let dustTrend: HazardMonitorStatus['trend'] = 'stable';
  const dryBoost = r.humidity < 20 ? 0.2 : r.humidity < 35 ? 0.1 : 0;
  const dustScore = (r.windSpeed / 25) * 0.45 + (1 - r.visibility / 10) * 0.3 + dryBoost;
  if ((r.windSpeed >= THRESHOLDS.wind.red && r.humidity < 30) || dustScore >= 0.90) {
    dustRisk = 'red';
    dustProb = 0.88;
    dustTrend = 'rising';
  } else if ((r.windSpeed >= THRESHOLDS.wind.orange && r.humidity < 35) || dustScore >= 0.70) {
    dustRisk = 'orange';
    dustProb = 0.58;
    dustTrend = 'rising';
  } else if ((r.windSpeed >= THRESHOLDS.wind.yellow && r.humidity < 45) || dustScore >= 0.50) {
    dustRisk = 'yellow';
    dustProb = 0.32;
    dustTrend = r.windSpeed > 10 ? 'rising' : 'stable';
  }
  hazards.push({ hazardId: 'dust-storm', hazardName: '沙尘暴', riskLevel: dustRisk, probability: dustProb, trend: dustTrend });

  return hazards;
}

export function deriveHighestRisk(hazards: HazardMonitorStatus[]): HazardMonitorStatus['riskLevel'] {
  const order: Record<string, number> = { red: 4, orange: 3, yellow: 2, green: 1 };
  return hazards.reduce((top, h) => (order[h.riskLevel] > order[top] ? h.riskLevel : top), 'green' as HazardMonitorStatus['riskLevel']);
}

export function countAlerts(hazards: HazardMonitorStatus[]): number {
  return hazards.filter((h) => h.riskLevel !== 'green').length;
}

// --- Transform hourly data to ForecastPoint[] ---

export function transformHourlyToForecast(
  raw: { time: string[]; temperature_2m: number[]; precipitation: number[] },
  maxHours: number,
): ForecastPoint[] {
  if (!raw || !raw.time || raw.time.length === 0) return [];
  const len = Math.min(raw.time.length, maxHours);
  const points: ForecastPoint[] = [];
  for (let i = 0; i < len; i++) {
    points.push({
      time: raw.time[i],
      temperature: Math.round(raw.temperature_2m[i] * 10) / 10,
      precipitation: Math.round(raw.precipitation[i] * 10) / 10,
    });
  }
  return points;
}

// --- Generate deterministic fallback forecast ---

export function generateFallbackForecast(baseTemp: number, regionId: string, hours = 48): ForecastPoint[] {
  const points: ForecastPoint[] = [];
  const now = new Date();
  const wetRegions = ['jazan', 'jeddah', 'makkah', 'abha'];
  const isWet = wetRegions.includes(regionId);
  const hotRegions = ['riyadh', 'makkah', 'medina'];
  const isHot = hotRegions.includes(regionId);
  const diurnalAmp = isHot ? 7 : isWet ? 4 : 5;

  for (let i = 0; i < hours; i++) {
    const t = new Date(now.getTime() + i * 3600 * 1000);
    const hour = t.getHours();
    const diurnal = Math.sin(((hour - 6) / 24) * Math.PI * 2) * diurnalAmp;
    const chaos = ((regionId.charCodeAt(0) * (i + 1) * 17 + i * 11) % 43 - 21) / 10;
    const temp = +(baseTemp + diurnal + chaos).toFixed(1);

    const precipSeed = (regionId.charCodeAt(1) * (i + 7) * 13 + i * 19) % 100;
    const precip = !isWet
      ? (precipSeed > 95 ? +(precipSeed / 100 * 4).toFixed(1) : 0)
      : (precipSeed > 78 ? +(precipSeed / 100 * 6).toFixed(1) : 0);

    points.push({ time: t.toISOString(), temperature: temp, precipitation: precip });
  }
  return points;
}

// --- Build MonitorRegionData from transformed parts ---

export function buildRegionData(
  regionId: string,
  regionName: string,
  nameEn: string,
  lat: number,
  lon: number,
  mapX: number,
  mapY: number,
  readings: MonitorReading,
  forecast: ForecastPoint[],
  lastUpdate: string,
): MonitorRegionData {
  const hazards = assessHazards(readings, regionId);
  const highestRiskLevel = deriveHighestRisk(hazards);
  const activeAlertCount = countAlerts(hazards);

  return {
    regionId,
    regionName,
    nameEn,
    lat,
    lon,
    mapX,
    mapY,
    readings,
    hazards,
    activeAlertCount,
    highestRiskLevel,
    lastUpdate,
    forecast,
  };
}

// --- Fallback data builder ---

export function getFallbackData(hours = 48): {
  regions: MonitorRegionData[];
  summary: { totalRegions: number; activeAlerts: number; lastRefresh: string; nextRefresh: string };
} {
  const now = new Date();
  const lastRefresh = now.toISOString().replace('T', ' ').slice(0, 16);
  const nextRefresh = new Date(now.getTime() + 30 * 60 * 1000).toISOString().replace('T', ' ').slice(0, 16);
  const enriched = fallbackRegions.map((r) => ({
    ...r,
    readings: { ...r.readings, windGust: 0, fireIndex: 0, thunderstormProb: 0 },
    forecast: generateFallbackForecast(r.readings.temperature, r.regionId, hours),
  }));
  return {
    regions: enriched,
    summary: {
      totalRegions: fallbackRegions.length,
      activeAlerts: fallbackRegions.reduce((s, r) => s + r.activeAlertCount, 0),
      lastRefresh,
      nextRefresh,
    },
  };
}