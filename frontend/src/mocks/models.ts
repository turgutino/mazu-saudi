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
// models trained in reference_code/mazu-saudi-warning, plus the live fusion
// baseline used when the archived feature contract is unavailable.
// This array is a type-safety/fallback aid only; the app always fetches the
// live list via GET /api/v1/models (see services/predictionApi.ts).
export const models: ModelInfo[] = [
  {
    id: 'joblib-heatwave',
    name: 'HistGradientBoosting-高温',
    version: 'trained-2025-06-30',
    type: 'tree',
    icon: 'ri-sun-line',
    description: 'Scikit-learn HistGradientBoostingClassifier，基于 ERA5 归档数据训练的高温预测模型（含邻域特征）。',
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
    description: 'Scikit-learn HistGradientBoostingClassifier，基于 ERA5 归档数据训练的山洪预测模型。',
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
    description: 'Scikit-learn HistGradientBoostingClassifier，基于 ERA5 归档数据训练的沙尘暴预测模型。',
    supportedHazards: ['dust-storm'],
    lastTrained: '2025-06-30',
    metrics: {
      'dust-storm': { auc: 0.8866, pod: 0.5352, far: 0.865, csi: 0.1208, f1: 0.2156, brier: 0.0602 },
    },
  },
  {
    id: 'live-fusion-v1',
    name: '实时预报风险评分（规则基线）',
    version: 'v1.1.0',
    type: 'rule',
    icon: 'ri-node-tree',
    description: '使用 CMA 或 Open-Meteo 目标时刻预报与前24小时累计降水计算的透明风险评分；四灾种共用，未经观测频率校准。',
    supportedHazards: ['heavy-rain', 'extreme-heat', 'flash-flood', 'dust-storm'],
    lastTrained: 'N/A',
    metrics: {},
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
