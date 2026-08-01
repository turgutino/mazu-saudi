import type { PredictionResult } from '@/mocks/predictions';

type ScoreMetadata = Pick<PredictionResult, 'scoreSemantics'>;
type CalibrationMetadata = Pick<PredictionResult, 'isCalibrated' | 'calibrationMethod'>;

export function scoreLabel(prediction: ScoreMetadata): string {
  if (prediction.scoreSemantics === 'calibrated_hazard_probability') return '校准灾害概率';
  if (prediction.scoreSemantics === 'uncalibrated_proxy_event_score') return '未校准代理事件分数';
  return '未校准模型事件分数';
}

export function ambiguityLabel(value: number): string {
  if (value < 0.15) return '低模糊度';
  if (value < 0.25) return '中等模糊度';
  return '高模糊度';
}

export function calibrationLabel(prediction: CalibrationMetadata): string {
  if (!prediction.isCalibrated || prediction.calibrationMethod === 'none') return '未校准';
  return prediction.calibrationMethod === 'platt' ? 'Platt 校准' : 'Isotonic 校准';
}
