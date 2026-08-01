export interface GraphNode {
  id: string;
  label: string;
  type: 'case' | 'prediction' | 'model' | 'hazard' | 'region' | 'feature' | 'rule' | 'mechanism' | 'risk' | 'event' | 'warning';
  group: 'anchor' | 'input' | 'features' | 'rules' | 'mechanisms' | 'events';
  step: number;
  navigateTab?: string;
  navigateNodeId?: string;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: 'PRODUCED' | 'USES' | 'TRIGGERS' | 'SUPPORTED_BY' | 'ASSESSED_AS' | 'SIMILAR_TO' | 'RESULTS_IN' | 'PREDICTS' | 'HAS_ATTRIBUTION' | 'INSTANCE_OF' | 'FOR_REGION' | 'GENERATED';
  step: number;
}

export interface KnowledgeGraph {
  predictionId: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NodeGroup {
  key: string;
  label: string;
  icon: string;
  color: string;
  nodeIds: string[];
}

export const NODE_GROUPS: NodeGroup[] = [
  { key: 'anchor', label: '核心流程', icon: 'ri-links-line', color: '#ea580c', nodeIds: ['case-001', 'pred-001', 'risk-001', 'warning-001'] },
  { key: 'input', label: '输入与上下文', icon: 'ri-database-2-line', color: '#0d9488', nodeIds: ['model-ensemble', 'hazard-ff', 'region-jazan'] },
  { key: 'features', label: '特征贡献', icon: 'ri-bar-chart-2-line', color: '#16a34a', nodeIds: ['feat-cape', 'feat-pw', 'feat-precip', 'feat-vapor'] },
  { key: 'rules', label: '风险规则', icon: 'ri-checkbox-multiple-line', color: '#d97706', nodeIds: ['rule-orange', 'rule-region', 'rule-cape'] },
  { key: 'mechanisms', label: '物理机制', icon: 'ri-git-branch-line', color: '#b45309', nodeIds: ['mech-vapor', 'mech-terrain'] },
  { key: 'events', label: '历史事件', icon: 'ri-history-line', color: '#ca8a04', nodeIds: ['hist-2024', 'hist-2023'] },
];

export const TIMELINE_STEPS = [
  { step: 0, label: '预测案例', desc: 'ForecastCase 初始化' },
  { step: 1, label: '模型预测', desc: '模型生成预测结果' },
  { step: 2, label: '特征归因', desc: 'Tree SHAP 原始 log-odds 局部归因' },
  { step: 3, label: '规则触发', desc: '风险规则命中判断' },
  { step: 4, label: '物理机制', desc: '物理解释链构建' },
  { step: 5, label: '风险评估', desc: '综合风险等级输出' },
  { step: 6, label: '预警发布', desc: '相似事件与预警' },
];

export const graphData: KnowledgeGraph = {
  predictionId: 'pred-2026-07-30-001',
  nodes: [
    { id: 'case-001', label: 'ForecastCase\n吉赞·2026-07-31', type: 'case', group: 'anchor', step: 0 },
    { id: 'pred-001', label: 'Prediction\n山洪概率 0.82', type: 'prediction', group: 'anchor', step: 1 },
    { id: 'model-ensemble', label: 'ModelVersion\n多模型集成 v4.1.0', type: 'model', group: 'input', step: 1 },
    { id: 'hazard-ff', label: 'HazardType\n山洪', type: 'hazard', group: 'input', step: 1 },
    { id: 'region-jazan', label: 'Region\n吉赞', type: 'region', group: 'input', step: 1 },
    { id: 'feat-cape', label: 'CAPE\n2350 J/kg', type: 'feature', group: 'features', step: 2, navigateTab: 'features' },
    { id: 'feat-pw', label: '可降水量\n58 mm', type: 'feature', group: 'features', step: 2, navigateTab: 'features' },
    { id: 'feat-precip', label: '日降水\n42 mm', type: 'feature', group: 'features', step: 2, navigateTab: 'features' },
    { id: 'feat-vapor', label: '水汽输送\n22 g/kg', type: 'feature', group: 'features', step: 2, navigateTab: 'features' },
    { id: 'rule-orange', label: 'Rule\n暴雨橙色阈值', type: 'rule', group: 'rules', step: 3, navigateTab: 'rules' },
    { id: 'rule-region', label: 'Rule\n山洪敏感区域', type: 'rule', group: 'rules', step: 3, navigateTab: 'rules' },
    { id: 'rule-cape', label: 'Rule\nCAPE强对流阈值', type: 'rule', group: 'rules', step: 3, navigateTab: 'rules' },
    { id: 'mech-vapor', label: 'Mechanism\n水汽-对流路径', type: 'mechanism', group: 'mechanisms', step: 4, navigateTab: 'mechanisms' },
    { id: 'mech-terrain', label: 'Mechanism\n地形抬升路径', type: 'mechanism', group: 'mechanisms', step: 4, navigateTab: 'mechanisms' },
    { id: 'risk-001', label: 'RiskAssessment\n橙色预警', type: 'risk', group: 'anchor', step: 5 },
    { id: 'hist-2024', label: 'HistoricalEvent\n2024-08 吉赞山洪', type: 'event', group: 'events', step: 6, navigateTab: 'history' },
    { id: 'hist-2023', label: 'HistoricalEvent\n2023-07 吉达山洪', type: 'event', group: 'events', step: 6, navigateTab: 'history' },
    { id: 'warning-001', label: 'Warning\n山洪橙色预警', type: 'warning', group: 'anchor', step: 6 },
  ],
  edges: [
    { id: 'e1', source: 'case-001', target: 'pred-001', label: 'PRODUCED', type: 'PRODUCED', step: 1 },
    { id: 'e2', source: 'model-ensemble', target: 'pred-001', label: 'GENERATED', type: 'GENERATED', step: 1 },
    { id: 'e3', source: 'pred-001', target: 'region-jazan', label: 'FOR_REGION', type: 'FOR_REGION', step: 1 },
    { id: 'e4', source: 'pred-001', target: 'hazard-ff', label: 'PREDICTS', type: 'PREDICTS', step: 1 },
    { id: 'e5', source: 'pred-001', target: 'feat-cape', label: 'HAS_ATTRIBUTION', type: 'HAS_ATTRIBUTION', step: 2 },
    { id: 'e6', source: 'pred-001', target: 'feat-pw', label: 'HAS_ATTRIBUTION', type: 'HAS_ATTRIBUTION', step: 2 },
    { id: 'e7', source: 'pred-001', target: 'feat-precip', label: 'HAS_ATTRIBUTION', type: 'HAS_ATTRIBUTION', step: 2 },
    { id: 'e8', source: 'pred-001', target: 'feat-vapor', label: 'HAS_ATTRIBUTION', type: 'HAS_ATTRIBUTION', step: 2 },
    { id: 'e9', source: 'feat-cape', target: 'rule-cape', label: 'USES', type: 'USES', step: 3 },
    { id: 'e10', source: 'pred-001', target: 'rule-orange', label: 'TRIGGERS', type: 'TRIGGERS', step: 3 },
    { id: 'e11', source: 'pred-001', target: 'rule-region', label: 'TRIGGERS', type: 'TRIGGERS', step: 3 },
    { id: 'e12', source: 'rule-cape', target: 'mech-vapor', label: 'SUPPORTED_BY', type: 'SUPPORTED_BY', step: 4 },
    { id: 'e13', source: 'rule-orange', target: 'mech-vapor', label: 'SUPPORTED_BY', type: 'SUPPORTED_BY', step: 4 },
    { id: 'e14', source: 'rule-region', target: 'mech-terrain', label: 'SUPPORTED_BY', type: 'SUPPORTED_BY', step: 4 },
    { id: 'e15', source: 'pred-001', target: 'risk-001', label: 'ASSESSED_AS', type: 'ASSESSED_AS', step: 5 },
    { id: 'e16', source: 'risk-001', target: 'hist-2024', label: 'SIMILAR_TO', type: 'SIMILAR_TO', step: 6 },
    { id: 'e17', source: 'risk-001', target: 'hist-2023', label: 'SIMILAR_TO', type: 'SIMILAR_TO', step: 6 },
    { id: 'e18', source: 'risk-001', target: 'warning-001', label: 'RESULTS_IN', type: 'RESULTS_IN', step: 6 },
    { id: 'e19', source: 'feat-cape', target: 'mech-vapor', label: 'INSTANCE_OF', type: 'INSTANCE_OF', step: 4 },
    { id: 'e20', source: 'feat-precip', target: 'rule-orange', label: 'USES', type: 'USES', step: 3 },
  ],
};
