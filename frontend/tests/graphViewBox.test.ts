import assert from 'node:assert/strict';
import test from 'node:test';

import { createFittedGraphViewBox } from '../src/pages/graph/viewBox.ts';

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
