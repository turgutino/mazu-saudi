/**
 * API prediction contracts retained at the legacy import path while the
 * frontend moves toward generated OpenAPI types. This file contains no
 * runtime prediction fixtures.
 */

export interface FeatureContribution {
  feature: string;
  featureLabel: string;
  contribution: number;
  normalValue: number | null;
  actualValue: number | null;
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
  decisionScore: number;
  scoreSemantics: 'uncalibrated_event_score' | 'uncalibrated_proxy_event_score' | 'calibrated_hazard_probability';
  calibrationMethod: 'none' | 'platt' | 'isotonic';
  isCalibrated: boolean;
  predictedClass: string;
  ambiguity: number;
  ambiguityMethod: 'heuristic_probability_margin';
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
  rawIndicators: Record<string, number | null>;
  dataTier: 'tier1_real' | 'tier2_live' | 'tier3_synthetic';
  forecastSnapshotId?: string | null;
  forecastSource?: string | null;
  indicatorProvenanceVersion?: string | null;
}
