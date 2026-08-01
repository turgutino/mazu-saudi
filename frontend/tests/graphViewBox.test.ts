import assert from 'node:assert/strict';
import test from 'node:test';

import { createFittedGraphViewBox, createNodeLabelPreview } from '../src/pages/graph/viewBox.ts';

test('fits the initial graph viewport to the measured container', () => {
  assert.deepEqual(createFittedGraphViewBox({ width: 1440, height: 720 }), {
    x: -50,
    y: -50,
    w: 1540,
    h: 820,
  });
});

test('clamps invalid padding and empty dimensions', () => {
  assert.deepEqual(createFittedGraphViewBox({ width: 0, height: -10 }, -20), {
    x: 0,
    y: 0,
    w: 1,
    h: 1,
  });
});

test('shortens long graph labels without changing the source text', () => {
  const label = 'HistGradientBoostingClassifier极端高温模型\n训练版本2025-06-30';

  assert.deepEqual(createNodeLabelPreview(label, 12, 3), [
    'HistGradien…',
    '训练版本2025-06…',
  ]);
  assert.equal(label, 'HistGradientBoostingClassifier极端高温模型\n训练版本2025-06-30');
});

test('limits graph labels to three lines and marks omitted content', () => {
  assert.deepEqual(createNodeLabelPreview('第一行\n第二行\n第三行\n第四行', 6, 3), [
    '第一行',
    '第二行',
    '第三行…',
  ]);
});
