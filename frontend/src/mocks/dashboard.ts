export interface RegionRiskSummary {
  regionId: string;
  regionName: string;
  riskLevel: 'green' | 'yellow' | 'orange' | 'red';
}

export interface DashboardStats {
  totalPredictions: number;
  activeWarnings: number;
  modelsOnline: number;
  regionsMonitored: number;
  regionRisk: RegionRiskSummary[];
  lastUpdated: string | null;
}

export interface RecentActivity {
  id: string;
  type: 'prediction' | 'warning' | 'report';
  title: string;
  description: string;
  time: string;
  riskLevel?: 'green' | 'yellow' | 'orange' | 'red';
}

export interface WeeklyStat {
  day: string;
  predictions: number;
  warnings: number;
}