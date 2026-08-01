export type GraphNodeType = 'case' | 'prediction' | 'model' | 'hazard' | 'region' | 'feature' | 'snapshot' | 'indicator' | 'rule' | 'mechanism' | 'risk' | 'event' | 'warning' | 'source' | 'ontology';
export type GraphGroup = 'anchor' | 'input' | 'features' | 'rules' | 'mechanisms' | 'events' | 'sources';

export interface GraphNode {
  id: string;
  label: string;
  type: GraphNodeType;
  group: GraphGroup;
  step: number;
  navigateTab?: string;
  navigateNodeId?: string;
  evidenceKind: string;
  status: string;
  details: Record<string, string | number | boolean | null>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
  step: number;
  semantics: 'asserted' | 'derived' | 'computed';
  confidence?: number | null;
  rationale: string;
  evidenceIds: string[];
  details: Record<string, string | number | boolean | null>;
}

export interface KnowledgeGraph {
  predictionId: string;
  graphVersion: string;
  ontologyId: string;
  ontologyVersion: string;
  generatedAt: string;
  disclaimer: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export async function fetchKnowledgeGraph(predictionId: string): Promise<KnowledgeGraph> {
  const response = await fetch(`${API_BASE}/knowledge-graph/${encodeURIComponent(predictionId)}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`图谱加载失败 (${response.status}): ${detail}`);
  }
  return response.json() as Promise<KnowledgeGraph>;
}
