export interface FeatureContribution {
  feature: string;
  featureLabel: string;
  contribution: number;
  normalValue: number | null;
  actualValue: number;
  unit: string;
}

export interface RuleHit {
  ruleId: string;
  ruleName: string;
  condition: string;
  actualValue: string;
  threshold: string;
  met: boolean;
  weight: number;
}

export interface MechanismStep {
  step: number;
  description: string;
  indicator: string;
  value: string;
  compatibility?: number;
}

export interface MechanismPath {
  pathId: string;
  pathName: string;
  confidence: 'high' | 'medium' | 'low';
  supportScore?: number;
  summary?: string;
  evidenceIds?: string[];
  steps: MechanismStep[];
}

export interface SimilarityDimension {
  key: string;
  label: string;
  score: number;
  weight: number;
  explanation: string;
}

export interface HistoricalEvent {
  eventId: string;
  date: string;
  region: string;
  hazard: string;
  description: string;
  similarity: number;
  similarityDimensions?: SimilarityDimension[];
  dataCoverage?: number;
  verificationStatus?: string;
  sourceTitle?: string;
  sourceUrl?: string | null;
  maxRainfall?: number | null;
  maxTemp?: number | null;
  impact: string;
}

export interface PredictionResult {
  predictionId: string;
  caseId: string;
  modelId: string;
  modelVersion: string;
  modelName: string;
  hazard: string;
  hazardLabel: string;
  regionId: string;
  regionName: string;
  targetTime: string;
  leadTimeHours: number;
  initialTime: string;
  probability: number;
  calibratedProbability: number;
  predictedClass: string;
  uncertainty: number;
  attributionMethod?: string | null;
  attributionOutput?: string | null;
  attributionBaseValue?: number | null;
  attributionModelOutput?: number | null;
  features: FeatureContribution[];
  ruleHits: RuleHit[];
  mechanisms: MechanismPath[];
  similarEvents: HistoricalEvent[];
  riskLevel: 'green' | 'yellow' | 'orange' | 'red';
  riskLabel: string;
  riskDescription: string;
  inputHash: string;
  createdAt: string;
  // Dataset-building provenance (not currently rendered in the UI): the raw
  // indicator values actually fed to the model, and which of the 3 tiers
  // (real archived data / live API / synthetic placeholder) produced them.
  rawIndicators: Record<string, number>;
  dataTier: 'tier1_real' | 'tier2_live' | 'tier3_synthetic';
  forecastSnapshotId?: string | null;
  forecastSource?: string | null;
}

export const predictions: PredictionResult[] = [
  {
    predictionId: 'pred-2026-07-30-001',
    caseId: 'case-2026-07-30-001',
    modelId: 'ensemble-v4',
    modelVersion: 'v4.1.0',
    modelName: '多模型集成',
    hazard: 'flash-flood',
    hazardLabel: '山洪',
    regionId: 'jazan',
    regionName: '吉赞',
    targetTime: '2026-07-31T18:00:00Z',
    leadTimeHours: 24,
    initialTime: '2026-07-30T18:00:00Z',
    probability: 0.78,
    calibratedProbability: 0.82,
    predictedClass: 'high',
    uncertainty: 0.15,
    features: [
      { feature: 'cape', featureLabel: 'CAPE', contribution: 0.21, normalValue: 800, actualValue: 2350, unit: 'J/kg' },
      { feature: 'pw', featureLabel: '可降水量', contribution: 0.17, normalValue: 35, actualValue: 58, unit: 'mm' },
      { feature: 'daily_precip', featureLabel: '日降水预测', contribution: 0.14, normalValue: 5, actualValue: 42, unit: 'mm' },
      { feature: 'vapor_850', featureLabel: '850hPa水汽输送', contribution: 0.08, normalValue: 8, actualValue: 22, unit: 'g/kg' },
      { feature: 'shear_500', featureLabel: '500hPa风切变', contribution: 0.06, normalValue: 12, actualValue: 28, unit: 'm/s' },
      { feature: 'rh_700', featureLabel: '700hPa相对湿度', contribution: 0.05, normalValue: 60, actualValue: 92, unit: '%' },
    ],
    ruleHits: [
      { ruleId: 'r-001', ruleName: '暴雨概率橙色阈值', condition: 'calibrated_probability >= 0.70', actualValue: '0.82', threshold: '0.70', met: true, weight: 3 },
      { ruleId: 'r-002', ruleName: '山洪敏感区域', condition: 'region_sensitivity == high', actualValue: 'high', threshold: 'high', met: true, weight: 2 },
      { ruleId: 'r-003', ruleName: 'CAPE强对流阈值', condition: 'cape >= 2000', actualValue: '2350', threshold: '2000', met: true, weight: 2 },
      { ruleId: 'r-004', ruleName: '日降水橙色阈值', condition: 'daily_precip >= 30', actualValue: '42', threshold: '30', met: true, weight: 1 },
      { ruleId: 'r-005', ruleName: '红色预警降水阈值', condition: 'daily_precip >= 50', actualValue: '42', threshold: '50', met: false, weight: 0 },
    ],
    mechanisms: [
      {
        pathId: 'mech-001',
        pathName: '水汽输送-对流触发路径',
        confidence: 'high',
        steps: [
          { step: 1, description: '红海异常水汽蒸发', indicator: 'SST异常', value: '+1.8°C' },
          { step: 2, description: '850hPa西南暖湿气流输送', indicator: '水汽通量', value: '22 g/kg' },
          { step: 3, description: '大气可降水量显著升高', indicator: 'PW', value: '58 mm' },
          { step: 4, description: 'CAPE累积达到强对流阈值', indicator: 'CAPE', value: '2350 J/kg' },
          { step: 5, description: '对流触发，强降水概率上升', indicator: '降水概率', value: '82%' },
        ],
      },
      {
        pathId: 'mech-002',
        pathName: '地形抬升增强路径',
        confidence: 'medium',
        steps: [
          { step: 1, description: '吉赞东部山地地形', indicator: '海拔', value: '2000m+' },
          { step: 2, description: '西南气流受地形抬升', indicator: '垂直速度', value: '0.8 m/s' },
          { step: 3, description: '地形强迫上升增强降水', indicator: '地形降水增强', value: '+35%' },
        ],
      },
    ],
    similarEvents: [
      { eventId: 'hist-001', date: '2024-08-12', region: '吉赞', hazard: '山洪', description: '吉赞地区短时强降水引发山洪，24小时降水量达68mm', similarity: 0.89, maxRainfall: 68, impact: '局部道路中断，3处居民区受影响' },
      { eventId: 'hist-002', date: '2023-07-28', region: '吉达', hazard: '山洪', description: '吉达北部山区暴雨引发山洪', similarity: 0.76, maxRainfall: 55, impact: '交通受阻，无人员伤亡' },
      { eventId: 'hist-003', date: '2025-09-03', region: '麦加', hazard: '山洪', description: '麦加地区强对流天气，伴有雷暴和短时强降水', similarity: 0.71, maxRainfall: 45, impact: '朝觐区域临时疏散' },
    ],
    riskLevel: 'orange',
    riskLabel: '橙色预警',
    riskDescription: '暴雨概率0.82超过橙色阈值0.70；吉赞属于山洪高敏感区域；降水和CAPE两条规则同时命中；因此输出橙色山洪风险。',
    inputHash: 'a3f8c2e1b9d4',
    createdAt: '2026-07-30T18:05:23Z',
    rawIndicators: { cape: 2350, pw: 58, daily_precip: 42, vapor_850: 22, shear_500: 28, rh_700: 92 },
    dataTier: 'tier1_real',
  },
  {
    predictionId: 'pred-2026-07-30-002',
    caseId: 'case-2026-07-30-002',
    modelId: 'xgb-v3',
    modelVersion: 'v3.2.1',
    modelName: 'XGBoost',
    hazard: 'extreme-heat',
    hazardLabel: '极端高温',
    regionId: 'riyadh',
    regionName: '利雅得',
    targetTime: '2026-08-01T15:00:00Z',
    leadTimeHours: 48,
    initialTime: '2026-07-30T15:00:00Z',
    probability: 0.65,
    calibratedProbability: 0.68,
    predictedClass: 'moderate',
    uncertainty: 0.22,
    features: [
      { feature: 't850', featureLabel: '850hPa温度', contribution: 0.19, normalValue: 28, actualValue: 34, unit: '°C' },
      { feature: 't2m', featureLabel: '2m气温预测', contribution: 0.16, normalValue: 42, actualValue: 48, unit: '°C' },
      { feature: 'rh_surface', featureLabel: '地表相对湿度', contribution: 0.11, normalValue: 15, actualValue: 6, unit: '%' },
      { feature: 'h500', featureLabel: '500hPa位势高度', contribution: 0.08, normalValue: 5900, actualValue: 5970, unit: 'gpm' },
    ],
    ruleHits: [
      { ruleId: 'r-101', ruleName: '高温黄色阈值', condition: 't2m >= 47', actualValue: '48', threshold: '47', met: true, weight: 2 },
      { ruleId: 'r-102', ruleName: '高温高敏感区域', condition: 'region_sensitivity == high', actualValue: 'high', threshold: 'high', met: true, weight: 2 },
    ],
    mechanisms: [
      {
        pathId: 'mech-101',
        pathName: '副高控制高温路径',
        confidence: 'high',
        steps: [
          { step: 1, description: '副热带高压异常西伸', indicator: '500hPa位势高度', value: '5970 gpm' },
          { step: 2, description: '下沉气流增强，云量减少', indicator: '总云量', value: '<5%' },
          { step: 3, description: '地表辐射加热加剧', indicator: '地表净辐射', value: '+25%' },
          { step: 4, description: '近地面温度持续攀升', indicator: '2m温度', value: '48°C' },
        ],
      },
    ],
    similarEvents: [
      { eventId: 'hist-101', date: '2025-07-15', region: '利雅得', hazard: '极端高温', description: '利雅得持续高温，连续3天最高气温超过47°C', similarity: 0.85, maxTemp: 49, impact: '电力负荷创历史新高' },
    ],
    riskLevel: 'yellow',
    riskLabel: '黄色预警',
    riskDescription: '高温概率0.68超过黄色阈值；利雅得属于高温高敏感区域；850hPa温度和2m气温均处于高位。',
    inputHash: 'b7d2f1a4c8e6',
    createdAt: '2026-07-30T15:08:45Z',
    rawIndicators: { t850: 34, t2m: 48, rh_surface: 6, h500: 5970 },
    dataTier: 'tier2_live',
  },
  {
    predictionId: 'pred-2026-07-29-003',
    caseId: 'case-2026-07-29-003',
    modelId: 'convlstm-v1',
    modelVersion: 'v1.5.3',
    modelName: 'ConvLSTM',
    hazard: 'heavy-rain',
    hazardLabel: '暴雨',
    regionId: 'jeddah',
    regionName: '吉达',
    targetTime: '2026-07-31T06:00:00Z',
    leadTimeHours: 36,
    initialTime: '2026-07-29T18:00:00Z',
    probability: 0.72,
    calibratedProbability: 0.69,
    predictedClass: 'moderate',
    uncertainty: 0.28,
    features: [
      { feature: 'cape', featureLabel: 'CAPE', contribution: 0.18, normalValue: 700, actualValue: 1850, unit: 'J/kg' },
      { feature: 'pw', featureLabel: '可降水量', contribution: 0.15, normalValue: 38, actualValue: 52, unit: 'mm' },
      { feature: 'daily_precip', featureLabel: '日降水预测', contribution: 0.12, normalValue: 3, actualValue: 28, unit: 'mm' },
      { feature: 'vapor_850', featureLabel: '850hPa水汽输送', contribution: 0.09, normalValue: 10, actualValue: 18, unit: 'g/kg' },
      { feature: 'rh_700', featureLabel: '700hPa相对湿度', contribution: 0.07, normalValue: 65, actualValue: 85, unit: '%' },
    ],
    ruleHits: [
      { ruleId: 'r-001', ruleName: '暴雨概率黄色阈值', condition: 'calibrated_probability >= 0.60', actualValue: '0.69', threshold: '0.60', met: true, weight: 2 },
      { ruleId: 'r-006', ruleName: '日降水黄色阈值', condition: 'daily_precip >= 25', actualValue: '28', threshold: '25', met: true, weight: 1 },
    ],
    mechanisms: [
      {
        pathId: 'mech-201',
        pathName: '红海水汽输送路径',
        confidence: 'medium',
        steps: [
          { step: 1, description: '红海海表温度偏高', indicator: 'SST', value: '32°C' },
          { step: 2, description: '低层水汽通量增加', indicator: '850hPa比湿', value: '18 g/kg' },
          { step: 3, description: '大气可降水量上升', indicator: 'PW', value: '52 mm' },
          { step: 4, description: '降水概率上升', indicator: '降水概率', value: '69%' },
        ],
      },
    ],
    similarEvents: [
      { eventId: 'hist-201', date: '2024-11-22', region: '吉达', hazard: '暴雨', description: '吉达地区暴雨导致城市内涝', similarity: 0.73, maxRainfall: 35, impact: '部分低洼路段积水严重' },
    ],
    riskLevel: 'yellow',
    riskLabel: '黄色预警',
    riskDescription: '暴雨概率0.69超过黄色阈值0.60；日降水预测28mm超过黄色阈值25mm；不确定性较高（0.28），建议持续关注。',
    inputHash: 'c1e8f3d5a7b2',
    createdAt: '2026-07-29T18:12:30Z',
    rawIndicators: { cape: 1850, pw: 52, daily_precip: 28, vapor_850: 18, rh_700: 85 },
    dataTier: 'tier2_live',
  },
  {
    predictionId: 'pred-2026-07-30-004',
    caseId: 'case-2026-07-30-004',
    modelId: 'lgbm-v2',
    modelVersion: 'v2.8.0',
    modelName: 'LightGBM',
    hazard: 'dust-storm',
    hazardLabel: '沙尘暴',
    regionId: 'dammam',
    regionName: '达曼',
    targetTime: '2026-07-31T12:00:00Z',
    leadTimeHours: 24,
    initialTime: '2026-07-30T12:00:00Z',
    probability: 0.52,
    calibratedProbability: 0.49,
    predictedClass: 'low',
    uncertainty: 0.30,
    features: [
      { feature: 'wind_10m', featureLabel: '10m风速', contribution: 0.15, normalValue: 12, actualValue: 22, unit: 'm/s' },
      { feature: 'soil_moisture', featureLabel: '土壤湿度', contribution: 0.12, normalValue: 0.15, actualValue: 0.04, unit: 'm³/m³' },
      { feature: 'visibility', featureLabel: '能见度预测', contribution: 0.10, normalValue: 10, actualValue: 5, unit: 'km' },
      { feature: 'rh_surface', featureLabel: '地表相对湿度', contribution: 0.08, normalValue: 25, actualValue: 12, unit: '%' },
    ],
    ruleHits: [
      { ruleId: 'r-301', ruleName: '沙尘暴黄色阈值', condition: 'wind_10m >= 20', actualValue: '22', threshold: '20', met: true, weight: 1 },
    ],
    mechanisms: [
      {
        pathId: 'mech-301',
        pathName: '干燥强风路径',
        confidence: 'medium',
        steps: [
          { step: 1, description: '内陆沙漠异常干燥', indicator: '土壤湿度', value: '0.04 m³/m³' },
          { step: 2, description: '气压梯度增大产生强风', indicator: '10m风速', value: '22 m/s' },
          { step: 3, description: '沙尘扬起降低能见度', indicator: '能见度', value: '<5 km' },
        ],
      },
    ],
    similarEvents: [
      { eventId: 'hist-301', date: '2025-03-18', region: '达曼', hazard: '沙尘暴', description: '强沙尘暴袭击达曼地区，能见度不足1公里', similarity: 0.68, impact: '机场航班大面积延误' },
    ],
    riskLevel: 'green',
    riskLabel: '低风险',
    riskDescription: '沙尘暴概率0.49低于黄色阈值；虽然风速超过20m/s阈值，但缺乏其他支持性指标。不确定性较高，建议持续监测。',
    inputHash: 'd9f2e4b6a1c3',
    createdAt: '2026-07-30T12:08:10Z',
    rawIndicators: { wind_10m: 22, soil_moisture: 0.04, visibility: 5, rh_surface: 12 },
    dataTier: 'tier3_synthetic',
  },
];
