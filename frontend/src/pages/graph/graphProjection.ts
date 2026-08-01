import type { GraphEdge, GraphNode } from '../../services/knowledgeGraphApi.ts';

export const DEFAULT_ATTRIBUTION_LIMIT = 8;

export interface GraphProjection {
  nodeIds: Set<string>;
  indicatorTotal: number;
  visibleIndicatorCount: number;
  hiddenIndicatorCount: number;
}

function isIndicator(node: GraphNode): boolean {
  return node.type === 'indicator' || node.type === 'feature';
}

function indicatorEndpoint(edge: GraphEdge, indicatorIds: Set<string>): string | null {
  if (indicatorIds.has(edge.source)) return edge.source;
  if (indicatorIds.has(edge.target)) return edge.target;
  return null;
}

/**
 * Builds a display-only projection. The source graph is never mutated or
 * truncated: rule/mechanism evidence remains visible, then the strongest
 * remaining model attributions are selected by absolute Tree SHAP value.
 */
export function createKeyEvidenceProjection(
  nodes: GraphNode[],
  edges: GraphEdge[],
  attributionLimit = DEFAULT_ATTRIBUTION_LIMIT,
): GraphProjection {
  const indicatorIds = new Set(nodes.filter(isIndicator).map((node) => node.id));
  const requiredIndicatorIds = new Set<string>();

  for (const edge of edges) {
    if (edge.type !== 'USES' && edge.type !== 'CONSISTENT_WITH') continue;
    const indicatorId = indicatorEndpoint(edge, indicatorIds);
    if (indicatorId) requiredIndicatorIds.add(indicatorId);
  }

  const rankedAttributions = edges
    .filter((edge) => edge.type === 'HAS_ATTRIBUTION')
    .map((edge) => ({
      indicatorId: indicatorEndpoint(edge, indicatorIds),
      contribution: typeof edge.details?.contribution === 'number' && Number.isFinite(edge.details.contribution)
        ? edge.details.contribution
        : null,
    }))
    .filter((item): item is { indicatorId: string; contribution: number | null } => (
      item.indicatorId !== null && !requiredIndicatorIds.has(item.indicatorId)
    ))
    .sort((a, b) => {
      if (a.contribution === null && b.contribution !== null) return 1;
      if (a.contribution !== null && b.contribution === null) return -1;
      const contributionOrder = Math.abs(b.contribution ?? 0) - Math.abs(a.contribution ?? 0);
      return contributionOrder || a.indicatorId.localeCompare(b.indicatorId);
    });

  const remainingSlots = Math.max(0, Math.floor(attributionLimit));
  for (const item of rankedAttributions.slice(0, remainingSlots)) {
    requiredIndicatorIds.add(item.indicatorId);
  }

  const nodeIds = new Set(
    nodes
      .filter((node) => !isIndicator(node) || requiredIndicatorIds.has(node.id))
      .map((node) => node.id),
  );

  return {
    nodeIds,
    indicatorTotal: indicatorIds.size,
    visibleIndicatorCount: requiredIndicatorIds.size,
    hiddenIndicatorCount: Math.max(0, indicatorIds.size - requiredIndicatorIds.size),
  };
}
