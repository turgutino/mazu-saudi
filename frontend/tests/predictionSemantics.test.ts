import assert from 'node:assert/strict';
import test from 'node:test';

import { ambiguityLabel, calibrationLabel, scoreLabel } from '../src/services/predictionSemantics.ts';

const base = {
  scoreSemantics: 'uncalibrated_event_score',
  isCalibrated: false,
  calibrationMethod: 'none',
} as const;

test('labels uncalibrated event and proxy scores without calling them probabilities', () => {
  assert.equal(scoreLabel(base as never), '未校准模型事件分数');
  assert.equal(scoreLabel({ ...base, scoreSemantics: 'uncalibrated_proxy_event_score' } as never), '未校准代理事件分数');
});

test('only labels a score as calibrated when calibration metadata says so', () => {
  assert.equal(calibrationLabel(base as never), '未校准');
  assert.equal(calibrationLabel({ ...base, scoreSemantics: 'calibrated_hazard_probability', isCalibrated: true, calibrationMethod: 'platt' } as never), 'Platt 校准');
});

test('describes the heuristic as ambiguity rather than an uncertainty interval', () => {
  assert.equal(ambiguityLabel(0.1), '低模糊度');
  assert.equal(ambiguityLabel(0.2), '中等模糊度');
  assert.equal(ambiguityLabel(0.3), '高模糊度');
});
