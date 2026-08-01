export interface ModelMetrics {
  auc: number;
  pod: number;
  far: number;
  csi: number;
  f1: number;
  brier: number;
}

export interface ModelInfo {
  id: string;
  name: string;
  version: string;
  type: 'tree' | 'deep' | 'physical' | 'ensemble' | 'rule';
  icon: string;
  description: string;
  supportedHazards: string[];
  lastTrained: string;
  metrics: Record<string, ModelMetrics>;
}

// Mirrors backend/app/data/models.py -- the real HistGradientBoostingClassifier
// models trained in reference_code/mazu-saudi-warning, plus four lightweight
// API-compatible HGB models used for live forecasts.
// This array is a type-safety/fallback aid only; the app always fetches the
// live list via GET /api/v1/models (see services/predictionApi.ts).
export const models: ModelInfo[] = [
  {
    id: 'joblib-heatwave',
    name: 'HistGradientBoosting-高温',
    version: 'trained-2025-06-30',
    type: 'tree',
    icon: 'ri-sun-line',
    description: '基于前一日ERA5归档指标预测目标日高温（T+1日/24小时）的HistGradientBoostingClassifier，含邻域特征。',
    supportedHazards: ['extreme-heat'],
    lastTrained: '2025-06-30',
    metrics: {
      'extreme-heat': { auc: 0.9706, pod: 0.8488, far: 0.3879, csi: 0.5519, f1: 0.7112, brier: 0.0304 },
    },
  },
  {
    id: 'joblib-flash_flood',
    name: 'HistGradientBoosting-山洪',
    version: 'trained-2025-06-30',
    type: 'tree',
    icon: 'ri-flood-line',
    description: '基于前一日ERA5归档指标预测目标日山洪风险（T+1日/24小时）的HistGradientBoostingClassifier。',
    supportedHazards: ['flash-flood'],
    lastTrained: '2025-06-30',
    metrics: {
      'flash-flood': { auc: 0.8732, pod: 0.1004, far: 0.8026, csi: 0.0713, f1: 0.1331, brier: 0.0063 },
    },
  },
  {
    id: 'joblib-dust_storm',
    name: 'HistGradientBoosting-沙尘暴',
    version: 'trained-2025-06-30',
    type: 'tree',
    icon: 'ri-windy-line',
    description: '基于前一日ERA5归档指标预测目标日沙尘暴代理事件（T+1日/24小时）的HistGradientBoostingClassifier。',
    supportedHazards: ['dust-storm'],
    lastTrained: '2025-06-30',
    metrics: {
      'dust-storm': { auc: 0.8866, pod: 0.5352, far: 0.865, csi: 0.1208, f1: 0.2156, brier: 0.0602 },
    },
  },
  {
    id: 'live-api-hgb-heavy_rain', name: 'API兼容HGB-强降雨', version: 'live-api-daily-v1',
    type: 'tree', icon: 'ri-rainy-line',
    description: '第三方逐小时预报聚合后运行；标签为日降水≥25 mm代理事件，测试分数不代表独立预报技巧。',
    supportedHazards: ['heavy-rain'], lastTrained: '2025-12-31',
    metrics: { 'heavy-rain': { auc: 1, pod: 1, far: 0, csi: 1, f1: 1, brier: 0 } },
  },
  {
    id: 'live-api-hgb-heatwave', name: 'API兼容HGB-高温', version: 'live-api-daily-v1',
    type: 'tree', icon: 'ri-sun-line',
    description: '第三方逐小时预报聚合后运行；使用2025归档高温标签训练，概率尚未校准。',
    supportedHazards: ['extreme-heat'], lastTrained: '2025-12-31',
    metrics: { 'extreme-heat': { auc: 0.9846, pod: 0.9258, far: 0.5161, csi: 0.4658, f1: 0.6356, brier: 0.0387 } },
  },
  {
    id: 'live-api-hgb-flash_flood', name: 'API兼容HGB-山洪', version: 'live-api-daily-v1',
    type: 'tree', icon: 'ri-flood-line',
    description: '第三方逐小时预报聚合后运行；使用2025归档教师代理标签训练，概率尚未校准。',
    supportedHazards: ['flash-flood'], lastTrained: '2025-12-31',
    metrics: { 'flash-flood': { auc: 0.8421, pod: 0.3406, far: 0.8166, csi: 0.1354, f1: 0.2384, brier: 0.0074 } },
  },
  {
    id: 'live-api-hgb-dust_storm', name: 'API兼容HGB-沙尘暴', version: 'live-api-daily-v1',
    type: 'tree', icon: 'ri-windy-line',
    description: '第三方逐小时预报聚合后运行；使用2025归档指标构造的版本化代理标签训练，概率尚未校准。',
    supportedHazards: ['dust-storm'], lastTrained: '2025-12-31',
    metrics: { 'dust-storm': { auc: 0.9901, pod: 0.9202, far: 0.6236, csi: 0.3645, f1: 0.5343, brier: 0.0241 } },
  },
];

export const METRIC_LABELS: Record<string, { name: string; description: string; higherIsBetter: boolean }> = {
  auc: { name: 'AUC', description: '模型区分正负样本的整体能力，越接近 1 越好', higherIsBetter: true },
  pod: { name: '命中率 POD', description: '实际发生且被正确预测的比例（召回率）', higherIsBetter: true },
  far: { name: '空报率 FAR', description: '预测发生但实际未发生的比例，越低越好', higherIsBetter: false },
  csi: { name: '关键成功指数 CSI', description: '命中次数 / (命中 + 漏报 + 空报)，综合衡量预报水平', higherIsBetter: true },
  f1: { name: 'F1 分数', description: '命中率与精准率的调和平均', higherIsBetter: true },
  brier: { name: 'Brier 分数', description: '概率预测的校准误差，越接近 0 越好', higherIsBetter: false },
};
