import type { PredictionResult } from '@/mocks/predictions';

type ScoreMetadata = Pick<PredictionResult, 'scoreSemantics'>;
type CalibrationMetadata = Pick<PredictionResult, 'isCalibrated' | 'calibrationMethod'>;
type Lang = 'zh' | 'en';

// Default to 'zh' so existing callers (and existing tests, which assert the
// exact Chinese strings) keep behaving identically; pass 'en' explicitly
// from a component that has access to the current i18n language.
export function scoreLabel(prediction: ScoreMetadata, lang: Lang = 'zh'): string {
  if (lang === 'en') {
    if (prediction.scoreSemantics === 'calibrated_hazard_probability') return 'Calibrated Hazard Probability';
    if (prediction.scoreSemantics === 'uncalibrated_proxy_event_score') return 'Uncalibrated Proxy Event Score';
    return 'Uncalibrated Model Event Score';
  }
  if (prediction.scoreSemantics === 'calibrated_hazard_probability') return '校准灾害概率';
  if (prediction.scoreSemantics === 'uncalibrated_proxy_event_score') return '未校准代理事件分数';
  return '未校准模型事件分数';
}

export function ambiguityLabel(value: number, lang: Lang = 'zh'): string {
  if (lang === 'en') {
    if (value < 0.15) return 'Low Ambiguity';
    if (value < 0.25) return 'Medium Ambiguity';
    return 'High Ambiguity';
  }
  if (value < 0.15) return '低模糊度';
  if (value < 0.25) return '中等模糊度';
  return '高模糊度';
}

export function calibrationLabel(prediction: CalibrationMetadata, lang: Lang = 'zh'): string {
  if (lang === 'en') {
    if (!prediction.isCalibrated || prediction.calibrationMethod === 'none') return 'Uncalibrated';
    return prediction.calibrationMethod === 'platt' ? 'Platt Calibration' : 'Isotonic Calibration';
  }
  if (!prediction.isCalibrated || prediction.calibrationMethod === 'none') return '未校准';
  return prediction.calibrationMethod === 'platt' ? 'Platt 校准' : 'Isotonic 校准';
}
