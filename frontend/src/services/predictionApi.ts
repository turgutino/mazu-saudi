import type { PredictionResult } from '@/mocks/predictions';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

async function parseResponse(response: Response): Promise<PredictionResult> {
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`预测服务错误 (${response.status}): ${body}`);
  }
  return response.json() as Promise<PredictionResult>;
}

export function createPrediction(request: {
  regionId: string;
  hazard: string;
  leadTimeHours: number;
  modelId: string;
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
