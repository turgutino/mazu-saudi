import assert from 'node:assert/strict';
import test from 'node:test';

import { createKeyEvidenceProjection } from '../src/pages/graph/graphProjection.ts';
import type { GraphEdge, GraphNode } from '../src/services/knowledgeGraphApi.ts';

function node(id: string, type: GraphNode['type'] = 'indicator'): GraphNode {
  return {
    id,
    label: id,
    type,
    group: type === 'indicator' ? 'features' : 'input',
    step: 2,
    evidenceKind: 'test',
    status: 'available',
    details: {},
  };
}

function edge(id: string, source: string, target: string, type: string, contribution?: number): GraphEdge {
  return {
    id,
    source,
    target,
    type,
    label: type,
    step: 2,
    semantics: type === 'HAS_ATTRIBUTION' ? 'computed' : 'asserted',
    rationale: 'test',
    evidenceIds: [],
    details: contribution === undefined ? {} : { contribution },
  };
}

test('keeps non-indicators, mechanism/rule inputs, and the strongest remaining attributions', () => {
  const nodes = [node('model', 'model'), node('rule', 'rule'), node('mechanism', 'mechanism')];
  const edges: GraphEdge[] = [];
  for (let index = 0; index < 12; index += 1) {
    const id = `indicator-${index}`;
    nodes.push(node(id));
    edges.push(edge(`shap-${index}`, 'prediction', id, 'HAS_ATTRIBUTION', index - 6));
  }
  edges.push(edge('rule-use', 'indicator-5', 'rule', 'USES'));
  edges.push(edge('mechanism-use', 'indicator-6', 'mechanism', 'CONSISTENT_WITH'));

  const projection = createKeyEvidenceProjection(nodes, edges, 3);

  assert.equal(projection.indicatorTotal, 12);
  assert.equal(projection.visibleIndicatorCount, 5);
  assert.equal(projection.hiddenIndicatorCount, 7);
  assert.ok(projection.nodeIds.has('model'));
  assert.ok(projection.nodeIds.has('indicator-5'));
  assert.ok(projection.nodeIds.has('indicator-6'));
  assert.ok(projection.nodeIds.has('indicator-0'));
  assert.ok(projection.nodeIds.has('indicator-11'));
  assert.ok(projection.nodeIds.has('indicator-1'));
  assert.ok(!projection.nodeIds.has('indicator-4'));
});

test('uses deterministic ordering and puts missing contribution values last', () => {
  const nodes = [node('indicator-b'), node('indicator-a'), node('indicator-missing')];
  const edges = [
    edge('b', 'prediction', 'indicator-b', 'HAS_ATTRIBUTION', -2),
    edge('a', 'prediction', 'indicator-a', 'HAS_ATTRIBUTION', 2),
    edge('missing', 'prediction', 'indicator-missing', 'HAS_ATTRIBUTION'),
  ];

  const projection = createKeyEvidenceProjection(nodes, edges, 1);

  assert.deepEqual([...projection.nodeIds], ['indicator-a']);
});

test('does not mutate the complete graph response', () => {
  const nodes = [node('indicator-a'), node('indicator-b')];
  const edges = [edge('a', 'prediction', 'indicator-a', 'HAS_ATTRIBUTION', 1)];
  const originalNodes = structuredClone(nodes);
  const originalEdges = structuredClone(edges);

  createKeyEvidenceProjection(nodes, edges, 0);

  assert.deepEqual(nodes, originalNodes);
  assert.deepEqual(edges, originalEdges);
});
