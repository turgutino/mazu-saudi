export interface DashboardStats {
  totalPredictions: number;
  activeWarnings: number;
  modelsOnline: number;
  regionsMonitored: number;
}

export interface RecentActivity {
  id: string;
  type: 'prediction' | 'warning' | 'report';
  title: string;
  description: string;
  time: string;
  riskLevel?: 'green' | 'yellow' | 'orange' | 'red';
}

export const dashboardStats: DashboardStats = {
  totalPredictions: 1284,
  activeWarnings: 7,
  modelsOnline: 4,
  regionsMonitored: 8,
};

export const recentActivities: RecentActivity[] = [
  {
    id: 'act-001',
    type: 'prediction',
    title: '山洪橙色预警 — 吉赞',
    description: '多模型集成预测山洪概率0.82，触发橙色预警',
    time: '2026-07-30 18:05',
    riskLevel: 'orange',
  },
  {
    id: 'act-002',
    type: 'prediction',
    title: '高温黄色预警 — 利雅得',
    description: 'XGBoost预测极端高温概率0.68，触发黄色预警',
    time: '2026-07-30 15:08',
    riskLevel: 'yellow',
  },
  {
    id: 'act-003',
    type: 'report',
    title: '预测报告生成 — 吉赞山洪',
    description: '智能体完成吉赞山洪预测报告，包含特征贡献和物理机制解释',
    time: '2026-07-30 18:12',
  },
  {
    id: 'act-004',
    type: 'prediction',
    title: '沙尘暴低风险 — 达曼',
    description: 'LightGBM预测沙尘暴概率0.49，风险等级为绿色',
    time: '2026-07-30 12:08',
    riskLevel: 'green',
  },
  {
    id: 'act-005',
    type: 'prediction',
    title: '暴雨黄色预警 — 吉达',
    description: 'ConvLSTM预测暴雨概率0.69，触发黄色预警',
    time: '2026-07-29 18:12',
    riskLevel: 'yellow',
  },
  {
    id: 'act-006',
    type: 'warning',
    title: '模型更新 — 多模型集成 v4.1.0',
    description: '集成模型已更新至v4.1.0，新增沙尘暴预测支持',
    time: '2026-07-25 09:30',
  },
];

export const weeklyStats = [
  { day: '周一', predictions: 28, warnings: 3 },
  { day: '周二', predictions: 35, warnings: 5 },
  { day: '周三', predictions: 22, warnings: 2 },
  { day: '周四', predictions: 41, warnings: 7 },
  { day: '周五', predictions: 30, warnings: 4 },
  { day: '周六', predictions: 18, warnings: 1 },
  { day: '周日', predictions: 15, warnings: 2 },
];