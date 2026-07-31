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
  type: 'tree' | 'deep' | 'physical' | 'ensemble';
  icon: string;
  description: string;
  supportedHazards: string[];
  lastTrained: string;
  metrics: Record<string, ModelMetrics>;
}

export const models: ModelInfo[] = [
  {
    id: 'xgb-v3',
    name: 'XGBoost',
    version: 'v3.2.1',
    type: 'tree',
    icon: 'ri-braces-line',
    description: '梯度提升树模型，擅长处理表格气象特征，训练速度快，可解释性好。适合中小规模区域的快速部署和迭代。',
    supportedHazards: ['heavy-rain', 'extreme-heat', 'flash-flood'],
    lastTrained: '2026-07-15',
    metrics: {
      'heavy-rain': { auc: 0.891, pod: 0.842, far: 0.183, csi: 0.714, f1: 0.827, brier: 0.078 },
      'extreme-heat': { auc: 0.937, pod: 0.905, far: 0.094, csi: 0.831, f1: 0.903, brier: 0.042 },
      'flash-flood': { auc: 0.864, pod: 0.798, far: 0.227, csi: 0.658, f1: 0.781, brier: 0.089 },
    },
  },
  {
    id: 'lgbm-v2',
    name: 'LightGBM',
    version: 'v2.8.0',
    type: 'tree',
    icon: 'ri-stack-line',
    description: '轻量级梯度提升模型，内存占用低，训练和推理速度极快。适合大规模多区域并发预测和资源受限环境。',
    supportedHazards: ['heavy-rain', 'extreme-heat', 'dust-storm'],
    lastTrained: '2026-07-20',
    metrics: {
      'heavy-rain': { auc: 0.882, pod: 0.831, far: 0.195, csi: 0.698, f1: 0.814, brier: 0.083 },
      'extreme-heat': { auc: 0.941, pod: 0.912, far: 0.088, csi: 0.842, f1: 0.911, brier: 0.039 },
      'dust-storm': { auc: 0.865, pod: 0.791, far: 0.224, csi: 0.651, f1: 0.776, brier: 0.092 },
    },
  },
  {
    id: 'convlstm-v1',
    name: 'ConvLSTM',
    version: 'v1.5.3',
    type: 'deep',
    icon: 'ri-brain-line',
    description: '卷积长短时记忆网络，同时捕捉空间场和时间序列的依赖关系，对复杂对流系统表现优异。推理需要 GPU。',
    supportedHazards: ['heavy-rain', 'severe-convection', 'flash-flood'],
    lastTrained: '2026-07-10',
    metrics: {
      'heavy-rain': { auc: 0.913, pod: 0.871, far: 0.152, csi: 0.762, f1: 0.858, brier: 0.068 },
      'severe-convection': { auc: 0.872, pod: 0.823, far: 0.209, csi: 0.687, f1: 0.809, brier: 0.086 },
      'flash-flood': { auc: 0.885, pod: 0.834, far: 0.196, csi: 0.702, f1: 0.820, brier: 0.079 },
    },
  },
  {
    id: 'ensemble-v4',
    name: '多模型集成',
    version: 'v4.1.0',
    type: 'ensemble',
    icon: 'ri-group-line',
    description: 'XGBoost + LightGBM + ConvLSTM 贝叶斯加权集成，融合树模型鲁棒性与深度学习时空感知能力。',
    supportedHazards: ['heavy-rain', 'extreme-heat', 'flash-flood', 'severe-convection', 'dust-storm'],
    lastTrained: '2026-07-25',
    metrics: {
      'heavy-rain': { auc: 0.926, pod: 0.893, far: 0.127, csi: 0.798, f1: 0.883, brier: 0.058 },
      'extreme-heat': { auc: 0.952, pod: 0.928, far: 0.071, csi: 0.872, f1: 0.929, brier: 0.035 },
      'flash-flood': { auc: 0.907, pod: 0.862, far: 0.158, csi: 0.752, f1: 0.843, brier: 0.069 },
      'severe-convection': { auc: 0.895, pod: 0.848, far: 0.174, csi: 0.731, f1: 0.826, brier: 0.076 },
      'dust-storm': { auc: 0.883, pod: 0.815, far: 0.201, csi: 0.683, f1: 0.801, brier: 0.085 },
    },
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