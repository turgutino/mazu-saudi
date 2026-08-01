import type { PredictionResult } from '@/mocks/predictions';
import type { Region } from '@/mocks/regions';
import type { HazardType } from '@/mocks/hazards';
import type { ModelInfo } from '@/mocks/models';

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

export function fetchRegions(): Promise<Region[]> {
  return fetch(`${API_BASE}/regions`, {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<Region[]>(response, '区域列表加载失败'));
}

export function fetchHazards(): Promise<HazardType[]> {
  return fetch(`${API_BASE}/hazards`, {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<HazardType[]>(response, '灾种列表加载失败'));
}

export function fetchModels(): Promise<ModelInfo[]> {
  return fetch(`${API_BASE}/models`, {
    headers: { Accept: 'application/json' },
  }).then((response) => parseJson<ModelInfo[]>(response, '模型列表加载失败'));
}
