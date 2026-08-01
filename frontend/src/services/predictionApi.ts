import type { PredictionResult } from '@/mocks/predictions';
import type { Region } from '@/mocks/regions';
import type { HazardType } from '@/mocks/hazards';
import type { ModelInfo } from '@/mocks/models';
import type { DashboardStats, RecentActivity, WeeklyStat } from '@/mocks/dashboard';
import { withCache, ONE_HOUR_MS } from './cache';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

async function parseJson<T>(response: Response, errorLabel: string): Promise<T> {
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${errorLabel} (${response.status}): ${body}`);
  }
  return response.json() as Promise<T>;
}

async function parseResponse(response: Response): Promise<PredictionResult> {
  return parseJson<PredictionResult>(response, '预测服务错误');
}

export function createPrediction(request: {
  regionId: string;
  hazard: string;
  leadTimeHours: number;
  modelId: string;
  initialTime?: string;
  predictionMode: 'live' | 'historical';
}): Promise<PredictionResult> {
  return fetch(`${API_BASE}/predictions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(request),
  }).then(parseResponse);
}

export function fetchPrediction(predictionId: string): Promise<PredictionResult> {
  return fetch(`${API_BASE}/predictions/${encodeURIComponent(predictionId)}`, {
    headers: { Accept: 'application/json' },
  }).then(parseResponse);
}

export function fetchPredictionsList(): Promise<PredictionResult[]> {
  return fetch(`${API_BASE}/predictions`, {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<PredictionResult[]>(response, '预测列表加载失败'));
}

// Regions/hazards/models change rarely, so cache them in sessionStorage for
// an hour instead of re-fetching on every Workspace page visit.

export function fetchRegions(): Promise<Region[]> {
  return withCache('regions', ONE_HOUR_MS, () =>
    fetch(`${API_BASE}/regions`, {
      headers: { Accept: 'application/json' },
    }).then((response) => parseJson<Region[]>(response, '区域列表加载失败')),
  );
}

export function fetchHazards(): Promise<HazardType[]> {
  return withCache('hazards', ONE_HOUR_MS, () =>
    fetch(`${API_BASE}/hazards`, {
      headers: { Accept: 'application/json' },
    }).then((response) => parseJson<HazardType[]>(response, '灾种列表加载失败')),
  );
}

export function fetchModels(): Promise<ModelInfo[]> {
  return withCache('models', ONE_HOUR_MS, () =>
    fetch(`${API_BASE}/models`, {
      headers: { Accept: 'application/json' },
    }).then((response) => parseJson<ModelInfo[]>(response, '模型列表加载失败')),
  );
}

// Dashboard aggregates change whenever a new prediction is submitted, so
// unlike regions/hazards/models these are not cached.

export function fetchDashboardStats(): Promise<DashboardStats> {
  return fetch(`${API_BASE}/dashboard/stats`, {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<DashboardStats>(response, '仪表盘统计加载失败'));
}

export function fetchRecentActivities(): Promise<RecentActivity[]> {
  return fetch(`${API_BASE}/dashboard/activities`, {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<RecentActivity[]>(response, '近期动态加载失败'));
}

export function fetchWeeklyStats(): Promise<WeeklyStat[]> {
  return fetch(`${API_BASE}/dashboard/weekly-stats`, {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<WeeklyStat[]>(response, '周趋势加载失败'));
}
