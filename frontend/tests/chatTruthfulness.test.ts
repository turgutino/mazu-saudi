import assert from 'node:assert/strict';
import test from 'node:test';

import { generateResponse, type ChatContext } from '../src/mocks/chatResponses.ts';
import { splitChatText } from '../src/services/chatFormatting.ts';

const context: ChatContext = {
  hazardLabel: '山洪',
  regionName: '吉赞',
  riskLevel: '黄色预警',
  decisionScore: 0.42,
  scoreSemantics: 'uncalibrated_proxy_event_score',
  calibrationMethod: 'none',
  isCalibrated: false,
  ambiguity: 0.2,
  ambiguityMethod: 'heuristic_probability_margin',
  modelName: 'API兼容HGB-山洪',
  modelVersion: 'live-api-daily-v1',
  leadTimeHours: 24,
  dataTier: 'tier2_live',
  forecastSource: 'open-meteo',
  featureSummaries: ['24小时降水: SHAP +0.200'],
  triggeredRuleNames: ['山洪未校准代理事件分数黄色阈值'],
  mechanismNames: ['水汽与对流相容路径'],
  similarEventSummaries: [],
  predictionId: 'pred-test',
};

test('template states the real calibration and ambiguity boundaries', () => {
  const answer = generateResponse('这个结果的可信边界是什么？', context);
  assert.match(answer, /未校准代理事件分数/);
  assert.match(answer, /不是±误差或统计置信区间/);
  assert.doesNotMatch(answer, /经过概率校准后更接近真实发生频率/);
});

test('model answer uses stored provenance and does not invent an ensemble', () => {
  const answer = generateResponse('用了什么模型和数据？', context);
  assert.match(answer, /API兼容HGB-山洪/);
  assert.match(answer, /open-meteo/);
  assert.doesNotMatch(answer, /XGBoost|LightGBM|ECMWF|GFS|多模型集成/);
});

test('chat formatting preserves HTML as inert text segments', () => {
  assert.deepEqual(splitChatText('<img src=x onerror=alert(1)> **可信**'), [
    { text: '<img src=x onerror=alert(1)> ', strong: false },
    { text: '可信', strong: true },
    { text: '', strong: false },
  ]);
});
