export type Locale = "zh" | "en";
export type Hazard = "heatwave" | "flash_flood" | "dust_storm";
export type FieldLayer = "probability" | "rule_risk" | "uncertainty";

export interface Health {
  status: string;
  mode: "historical_exercise" | "archive";
  ready_for_inference: boolean;
  checks: Record<string, boolean>;
  missing: string[];
  llm_available: boolean;
}

export interface Config {
  product: { name: string; name_zh: string };
  cities: string[];
  hazards: Hazard[];
  date_range: { start: string; end: string };
  mode: string;
  boundaries: string[];
}

export interface Scenario {
  id: string;
  city: string;
  target_date: string;
  hazard: Hazard;
  kind: string;
  title_en: string;
  title_zh: string;
}

export interface Forecast {
  city: string;
  target_date: string;
  features_from_date: string;
  hazard: Hazard;
  probability: number;
  grid_cell: { lat: number; lon: number };
  elevation_m: number | null;
  terrain_note: string | null;
  impact_context: { city_population_2022_census: number; source: string; note: string } | null;
  reflexive_check: {
    detection_engine_risk_score: number;
    detection_engine_conditions_fired: string[];
    consistency: string;
    note?: string;
  } | null;
  model_verified_roc_auc: number;
  meteorological_metrics: Record<string, number>;
  uncertainty: { mean: number; std: number; range: [number, number]; n_members: number };
}

export interface Evidence {
  hazard: Hazard;
  claim_boundary: string;
  contributing_indicators: string[];
  mechanisms: Array<{
    mechanism: string;
    description: string;
    literature_grounded?: boolean;
    citations: Array<{
      citation?: string;
      url?: string;
      review_status?: string;
      verification_scope?: string;
    }>;
  }>;
}

export interface Run {
  id: string;
  city: string;
  target_date: string;
  hazard: Hazard;
  locale: Locale;
  status: string;
  created_at: string;
  error: string | null;
  result: null | {
    contract_version: string;
    mode: string;
    operational_warning: boolean;
    scientific_evidence: string;
    forecast: Forecast;
    conditions: { city: string; date: string; indicators?: Record<string, number | null>; conditions?: Record<string, number | null> };
    evidence: Evidence;
    decision: { level: string; threshold: number; alert_candidate: boolean; policy: string };
    boundaries: string[];
  };
}

export interface FieldData {
  layer: FieldLayer;
  rows: number;
  columns: number;
  latitudes: number[];
  longitudes: number[];
  values: number[];
  minimum: number;
  maximum: number;
  cache: string;
}

export interface ReportItem {
  id: string;
  title: string;
  language: Locale;
  kind: string;
  url: string;
}
