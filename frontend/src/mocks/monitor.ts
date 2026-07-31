export interface MonitorReading {
  temperature: number;
  humidity: number;
  windSpeed: number;
  windDir: number;
  pressure: number;
  cape: number;
  pw: number;
  visibility: number;
  windGust: number;
  fireIndex: number;
  thunderstormProb: number;
}

export interface ForecastPoint {
  time: string;
  temperature: number;
  precipitation: number;
}

export interface HazardMonitorStatus {
  hazardId: string;
  hazardName: string;
  riskLevel: 'green' | 'yellow' | 'orange' | 'red';
  probability: number;
  trend: 'rising' | 'stable' | 'falling';
}

export interface MonitorRegionData {
  regionId: string;
  regionName: string;
  nameEn: string;
  lat: number;
  lon: number;
  mapX: number;
  mapY: number;
  readings: MonitorReading;
  hazards: HazardMonitorStatus[];
  activeAlertCount: number;
  highestRiskLevel: 'green' | 'yellow' | 'orange' | 'red';
  lastUpdate: string;
  forecast?: ForecastPoint[];
}

export const hazardTypes = [
  { id: 'heavy-rain', name: '暴雨', icon: 'ri-showers-line' },
  { id: 'extreme-heat', name: '极端高温', icon: 'ri-sun-line' },
  { id: 'flash-flood', name: '山洪', icon: 'ri-flood-line' },
  { id: 'severe-convection', name: '强对流', icon: 'ri-thunderstorms-line' },
  { id: 'dust-storm', name: '沙尘暴', icon: 'ri-windy-line' },
  { id: 'wildfire', name: '野火风险', icon: 'ri-fire-line' },
];

export const monitorRegions: MonitorRegionData[] = [
  {
    regionId: 'jazan',
    regionName: '吉赞',
    nameEn: 'Jazan',
    lat: 16.8892,
    lon: 42.5511,
    mapX: 38.9,
    mapY: 94.4,
    readings: { temperature: 33, humidity: 78, windSpeed: 8, windDir: 220, pressure: 1008, cape: 2350, pw: 58, visibility: 12, windGust: 14, fireIndex: 2, thunderstormProb: 68 },
    hazards: [
      { hazardId: 'heavy-rain', hazardName: '暴雨', riskLevel: 'yellow', probability: 0.65, trend: 'rising' },
      { hazardId: 'extreme-heat', hazardName: '极端高温', riskLevel: 'green', probability: 0.15, trend: 'stable' },
      { hazardId: 'flash-flood', hazardName: '山洪', riskLevel: 'orange', probability: 0.82, trend: 'rising' },
      { hazardId: 'severe-convection', hazardName: '强对流', riskLevel: 'yellow', probability: 0.58, trend: 'rising' },
      { hazardId: 'dust-storm', hazardName: '沙尘暴', riskLevel: 'green', probability: 0.08, trend: 'stable' },
    ],
    activeAlertCount: 2,
    highestRiskLevel: 'orange',
    lastUpdate: '2026-07-31 06:30',
  },
  {
    regionId: 'riyadh',
    regionName: '利雅得',
    nameEn: 'Riyadh',
    lat: 24.7136,
    lon: 46.6753,
    mapX: 57.6,
    mapY: 45.5,
    readings: { temperature: 46, humidity: 8, windSpeed: 12, windDir: 350, pressure: 1012, cape: 450, pw: 22, visibility: 8, windGust: 18, fireIndex: 5, thunderstormProb: 12 },
    hazards: [
      { hazardId: 'heavy-rain', hazardName: '暴雨', riskLevel: 'green', probability: 0.12, trend: 'falling' },
      { hazardId: 'extreme-heat', hazardName: '极端高温', riskLevel: 'yellow', probability: 0.68, trend: 'rising' },
      { hazardId: 'flash-flood', hazardName: '山洪', riskLevel: 'green', probability: 0.05, trend: 'stable' },
      { hazardId: 'severe-convection', hazardName: '强对流', riskLevel: 'green', probability: 0.18, trend: 'stable' },
      { hazardId: 'dust-storm', hazardName: '沙尘暴', riskLevel: 'yellow', probability: 0.42, trend: 'rising' },
    ],
    activeAlertCount: 1,
    highestRiskLevel: 'yellow',
    lastUpdate: '2026-07-31 06:30',
  },
  {
    regionId: 'jeddah',
    regionName: '吉达',
    nameEn: 'Jeddah',
    lat: 21.5433,
    lon: 39.1728,
    mapX: 23.5,
    mapY: 65.4,
    readings: { temperature: 38, humidity: 62, windSpeed: 10, windDir: 200, pressure: 1006, cape: 1850, pw: 52, visibility: 10, windGust: 16, fireIndex: 3, thunderstormProb: 69 },
    hazards: [
      { hazardId: 'heavy-rain', hazardName: '暴雨', riskLevel: 'yellow', probability: 0.69, trend: 'rising' },
      { hazardId: 'extreme-heat', hazardName: '极端高温', riskLevel: 'green', probability: 0.22, trend: 'stable' },
      { hazardId: 'flash-flood', hazardName: '山洪', riskLevel: 'green', probability: 0.35, trend: 'stable' },
      { hazardId: 'severe-convection', hazardName: '强对流', riskLevel: 'yellow', probability: 0.55, trend: 'rising' },
      { hazardId: 'dust-storm', hazardName: '沙尘暴', riskLevel: 'green', probability: 0.15, trend: 'stable' },
    ],
    activeAlertCount: 1,
    highestRiskLevel: 'yellow',
    lastUpdate: '2026-07-31 06:30',
  },
  {
    regionId: 'makkah',
    regionName: '麦加',
    nameEn: 'Makkah',
    lat: 21.3891,
    lon: 39.8579,
    mapX: 26.6,
    mapY: 66.3,
    readings: { temperature: 44, humidity: 25, windSpeed: 6, windDir: 180, pressure: 1009, cape: 520, pw: 30, visibility: 15, windGust: 10, fireIndex: 4, thunderstormProb: 28 },
    hazards: [
      { hazardId: 'heavy-rain', hazardName: '暴雨', riskLevel: 'green', probability: 0.28, trend: 'stable' },
      { hazardId: 'extreme-heat', hazardName: '极端高温', riskLevel: 'green', probability: 0.48, trend: 'stable' },
      { hazardId: 'flash-flood', hazardName: '山洪', riskLevel: 'green', probability: 0.18, trend: 'stable' },
      { hazardId: 'severe-convection', hazardName: '强对流', riskLevel: 'green', probability: 0.22, trend: 'stable' },
      { hazardId: 'dust-storm', hazardName: '沙尘暴', riskLevel: 'green', probability: 0.25, trend: 'stable' },
    ],
    activeAlertCount: 0,
    highestRiskLevel: 'green',
    lastUpdate: '2026-07-31 06:30',
  },
  {
    regionId: 'dammam',
    regionName: '达曼',
    nameEn: 'Dammam',
    lat: 26.4207,
    lon: 50.0888,
    mapX: 73.1,
    mapY: 34.9,
    readings: { temperature: 41, humidity: 45, windSpeed: 18, windDir: 310, pressure: 1010, cape: 380, pw: 28, visibility: 5, windGust: 22, fireIndex: 6, thunderstormProb: 15 },
    hazards: [
      { hazardId: 'heavy-rain', hazardName: '暴雨', riskLevel: 'green', probability: 0.15, trend: 'stable' },
      { hazardId: 'extreme-heat', hazardName: '极端高温', riskLevel: 'green', probability: 0.38, trend: 'stable' },
      { hazardId: 'flash-flood', hazardName: '山洪', riskLevel: 'green', probability: 0.08, trend: 'stable' },
      { hazardId: 'severe-convection', hazardName: '强对流', riskLevel: 'green', probability: 0.20, trend: 'stable' },
      { hazardId: 'dust-storm', hazardName: '沙尘暴', riskLevel: 'green', probability: 0.49, trend: 'rising' },
    ],
    activeAlertCount: 0,
    highestRiskLevel: 'green',
    lastUpdate: '2026-07-31 06:30',
  },
  {
    regionId: 'abha',
    regionName: '艾卜哈',
    nameEn: 'Abha',
    lat: 18.2164,
    lon: 42.5053,
    mapX: 38.7,
    mapY: 86.1,
    readings: { temperature: 28, humidity: 55, windSpeed: 5, windDir: 210, pressure: 1015, cape: 680, pw: 38, visibility: 18, windGust: 9, fireIndex: 1, thunderstormProb: 22 },
    hazards: [
      { hazardId: 'heavy-rain', hazardName: '暴雨', riskLevel: 'green', probability: 0.22, trend: 'stable' },
      { hazardId: 'extreme-heat', hazardName: '极端高温', riskLevel: 'green', probability: 0.08, trend: 'stable' },
      { hazardId: 'flash-flood', hazardName: '山洪', riskLevel: 'green', probability: 0.12, trend: 'stable' },
      { hazardId: 'severe-convection', hazardName: '强对流', riskLevel: 'green', probability: 0.18, trend: 'stable' },
      { hazardId: 'dust-storm', hazardName: '沙尘暴', riskLevel: 'green', probability: 0.10, trend: 'stable' },
    ],
    activeAlertCount: 0,
    highestRiskLevel: 'green',
    lastUpdate: '2026-07-31 06:30',
  },
  {
    regionId: 'medina',
    regionName: '麦地那',
    nameEn: 'Medina',
    lat: 24.5247,
    lon: 39.5692,
    mapX: 25.3,
    mapY: 46.7,
    readings: { temperature: 42, humidity: 18, windSpeed: 9, windDir: 340, pressure: 1011, cape: 410, pw: 24, visibility: 14, windGust: 13, fireIndex: 3, thunderstormProb: 18 },
    hazards: [
      { hazardId: 'heavy-rain', hazardName: '暴雨', riskLevel: 'green', probability: 0.18, trend: 'stable' },
      { hazardId: 'extreme-heat', hazardName: '极端高温', riskLevel: 'green', probability: 0.42, trend: 'stable' },
      { hazardId: 'flash-flood', hazardName: '山洪', riskLevel: 'green', probability: 0.10, trend: 'stable' },
      { hazardId: 'severe-convection', hazardName: '强对流', riskLevel: 'green', probability: 0.15, trend: 'stable' },
      { hazardId: 'dust-storm', hazardName: '沙尘暴', riskLevel: 'green', probability: 0.30, trend: 'stable' },
    ],
    activeAlertCount: 0,
    highestRiskLevel: 'green',
    lastUpdate: '2026-07-31 06:30',
  },
  {
    regionId: 'tabuk',
    regionName: '塔布克',
    nameEn: 'Tabuk',
    lat: 28.3835,
    lon: 36.5771,
    mapX: 11.7,
    mapY: 22.6,
    readings: { temperature: 39, humidity: 22, windSpeed: 14, windDir: 300, pressure: 1014, cape: 290, pw: 18, visibility: 6, windGust: 20, fireIndex: 5, thunderstormProb: 8 },
    hazards: [
      { hazardId: 'heavy-rain', hazardName: '暴雨', riskLevel: 'green', probability: 0.08, trend: 'stable' },
      { hazardId: 'extreme-heat', hazardName: '极端高温', riskLevel: 'green', probability: 0.35, trend: 'stable' },
      { hazardId: 'flash-flood', hazardName: '山洪', riskLevel: 'green', probability: 0.05, trend: 'stable' },
      { hazardId: 'severe-convection', hazardName: '强对流', riskLevel: 'green', probability: 0.12, trend: 'stable' },
      { hazardId: 'dust-storm', hazardName: '沙尘暴', riskLevel: 'yellow', probability: 0.52, trend: 'rising' },
    ],
    activeAlertCount: 1,
    highestRiskLevel: 'yellow',
    lastUpdate: '2026-07-31 06:30',
  },
];

export const monitorSummary = {
  totalRegions: 8,
  activeAlerts: 5,
  highestRiskRegion: '吉赞',
  highestRiskLevel: 'orange' as const,
  lastRefresh: '2026-07-31 06:30',
  nextRefresh: '2026-07-31 07:00',
};