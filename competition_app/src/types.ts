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

export interface OntologyNode {
  iri: string;
  local_name: string;
  resource_type: string;
  module: string | null;
  status: string | null;
  label: string;
  label_en: string | null;
  label_zh: string | null;
  definition_en: string | null;
  definition_zh: string | null;
}

export interface OntologyEdge {
  id: number;
  source: string;
  target: string;
  predicate: string;
  predicate_label: string;
}

export interface OntologyRelationView {
  ontology: {
    ontology_iri: string;
    version: string;
    source_sha256: string;
    loaded_at: string;
  };
  filters: { query: string; module: string | null };
  nodes: OntologyNode[];
  edges: OntologyEdge[];
  node_count: number;
  edge_count: number;
}

export interface KnowledgeGraphBuild {
  build_id: string;
  ontology_iri: string;
  ontology_version: string;
  ontology_sha256: string;
  input_root: string;
  input_manifest_sha256: string;
  scope_label: string;
  start_date: string;
  end_date: string;
  file_count: number;
  created_at: string;
  node_count: number;
  edge_count: number;
  assertion_count: number;
  episode_count: number;
  config: Record<string, unknown>;
}

export interface KnowledgeGraphNode {
  node_id: string;
  build_id: string;
  ontology_class_iri: string;
  concept_iri: string | null;
  label: string;
  spatial_key: string | null;
  start_time: string | null;
  end_time: string | null;
  properties: Record<string, unknown>;
}

export interface KnowledgeGraphEdge {
  edge_id: string;
  build_id: string;
  source_id: string;
  predicate_iri: string;
  target_id: string;
  properties: Record<string, unknown>;
}

export interface KnowledgeGraphView {
  build: KnowledgeGraphBuild | null;
  literature_run?: {
    run_id: string;
    build_id: string;
    model: string;
    prompt_version: string;
    publication_count: number;
    evidence_record_count: number;
    mechanism_assertion_count: number;
    created_at: string;
  } | null;
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface HazardExplanation {
  contract_version: string;
  hazard: {
    id: Hazard;
    label: string;
    target_state_iri: string;
    screening_state_iri: string;
    observational_target_state_iris: string[];
  };
  source_graph: { name: string; schema_version: string; purpose: string };
  indicators: Array<{
    id: string;
    label: string;
    description: string | null;
    relation_audit: Record<string, unknown>;
  }>;
  mechanisms: Array<{
    id: string;
    label: string;
    description: string | null;
    relation_audit: Record<string, unknown>;
    literature_support_available: boolean;
    citations: Array<{
      id: string;
      citation: string;
      title: string;
      verification_scope: string;
      review_status: string;
    }>;
  }>;
  evidence_gaps: Array<{
    code: string;
    subject_id: string;
    message: string;
    required_action: string;
  }>;
  observational_context: {
    status: string;
    global_build_id: string | null;
    related_assertions: Array<{
      assertion_id: string;
      label: string;
      source_state: { id: string; label: string };
      target_state: { id: string; label: string };
      lift: number;
      support_rate: number;
      evidence_class: string;
      use: "explanation_and_research_diagnostics_only";
    }>;
    boundary: string;
  };
  eligible_for_causal_explanation: false;
  boundaries: string[];
}

export interface GraphExplanationAblation {
  contract_version: string;
  scope: "explanation_coverage_only";
  forecast_model_changed: false;
  prediction_skill_evaluated: false;
  hallucination_rate_evaluated: false;
  with_graph: {
    mechanism_count: number;
    grounded_mechanism_count: number;
    citation_count: number;
    evidence_gap_count: number;
  };
  without_graph: {
    mechanism_count: 0;
    citation_count: 0;
    evidence_gap_count: 0;
    response_policy: string;
  };
  boundary: string;
}
