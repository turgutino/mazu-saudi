import type { PredictionResult } from '@/mocks/predictions';
import type { Region } from '@/mocks/regions';
import type { HazardType } from '@/mocks/hazards';
import type { ModelInfo } from '@/mocks/models';
import type { DashboardStats, RecentActivity, WeeklyStat } from '@/mocks/dashboard';
import { withCache, ONE_HOUR_MS } from './cache';
import i18n from '@/i18n';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

function currentLang(): 'zh' | 'en' {
  return i18n.language?.startsWith('zh') ? 'zh' : 'en';
}

function withLang(path: string): string {
  const separator = path.includes('?') ? '&' : '?';
  return `${API_BASE}${path}${separator}lang=${currentLang()}`;
}

async function parseJson<T>(response: Response, errorLabel: string): Promise<T> {
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${errorLabel} (${response.status}): ${body}`);
  }
  return response.json() as Promise<T>;
}

async function parseResponse(response: Response): Promise<PredictionResult> {
  return parseJson<PredictionResult>(response, i18n.t('errors.predictionService'));
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
    body: JSON.stringify({ ...request, lang: currentLang() }),
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
  }).then((response) => parseJson<PredictionResult[]>(response, i18n.t('errors.predictionsList')));
}

// Regions/hazards/models change rarely, so cache them in sessionStorage for
// an hour instead of re-fetching on every Workspace page visit. The cache
// key includes the current language so switching EN/ZH doesn't serve a
// stale-language cached response.

export function fetchRegions(): Promise<Region[]> {
  return withCache(`regions:${currentLang()}`, ONE_HOUR_MS, () =>
    fetch(withLang('/regions'), {
      headers: { Accept: 'application/json' },
    }).then((response) => parseJson<Region[]>(response, i18n.t('errors.regionsList'))),
  );
}

export function fetchHazards(): Promise<HazardType[]> {
  return withCache(`hazards:${currentLang()}`, ONE_HOUR_MS, () =>
    fetch(withLang('/hazards'), {
      headers: { Accept: 'application/json' },
    }).then((response) => parseJson<HazardType[]>(response, i18n.t('errors.hazardsList'))),
  );
}

export function fetchModels(): Promise<ModelInfo[]> {
  return withCache(`models:${currentLang()}`, ONE_HOUR_MS, () =>
    fetch(withLang('/models'), {
      headers: { Accept: 'application/json' },
    }).then((response) => parseJson<ModelInfo[]>(response, i18n.t('errors.modelsList'))),
  );
}

// Dashboard aggregates change whenever a new prediction is submitted, so
// unlike regions/hazards/models these are not cached.

export function fetchDashboardStats(): Promise<DashboardStats> {
  return fetch(withLang('/dashboard/stats'), {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<DashboardStats>(response, i18n.t('errors.dashboardStats')));
}

export function fetchRecentActivities(): Promise<RecentActivity[]> {
  return fetch(withLang('/dashboard/activities'), {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<RecentActivity[]>(response, i18n.t('errors.recentActivities')));
}

export function fetchWeeklyStats(): Promise<WeeklyStat[]> {
  return fetch(withLang('/dashboard/weekly-stats'), {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<WeeklyStat[]>(response, i18n.t('errors.weeklyStats')));
}
