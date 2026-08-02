import type { PredictionResult } from '@/mocks/predictions';
import { ambiguityLabel, calibrationLabel, scoreLabel } from '../services/predictionSemantics.ts';

export type ChatSource = 'llm' | 'keyword-fallback' | 'system';
export type ChatLang = 'zh' | 'en';

export interface ChatMessage {
  role: 'user' | 'agent';
  content: string;
  timestamp: number;
  source?: ChatSource;
}

export interface ChatContext {
  hazardLabel: string;
  regionName: string;
  riskLevel: string;
  decisionScore: number;
  scoreSemantics: PredictionResult['scoreSemantics'];
  calibrationMethod: PredictionResult['calibrationMethod'];
  isCalibrated: boolean;
  ambiguity: number;
  ambiguityMethod: PredictionResult['ambiguityMethod'];
  modelName: string;
  modelVersion: string;
  leadTimeHours: number;
  dataTier: PredictionResult['dataTier'];
  forecastSource?: string | null;
  featureSummaries: string[];
  triggeredRuleNames: string[];
  mechanismNames: string[];
  similarEventSummaries: string[];
  predictionId: string;
}

export const SUGGESTED_QUESTIONS = {
  zh: [
    { label: '这个结果的可信边界是什么？', icon: 'ri-shield-check-line' },
    { label: '模型分数为什么是这个值？', icon: 'ri-question-line' },
    { label: '有哪些真实的相似案例？', icon: 'ri-history-line' },
    { label: '风险等级是怎么定的？', icon: 'ri-alert-line' },
    { label: '机制解释是什么？', icon: 'ri-git-branch-line' },
    { label: '模型用了什么数据？', icon: 'ri-database-2-line' },
  ],
  en: [
    { label: 'What are the credibility boundaries of this result?', icon: 'ri-shield-check-line' },
    { label: 'Why is the model score this value?', icon: 'ri-question-line' },
    { label: 'Are there any real similar cases?', icon: 'ri-history-line' },
    { label: 'How was the risk level determined?', icon: 'ri-alert-line' },
    { label: 'What is the mechanism explanation?', icon: 'ri-git-branch-line' },
    { label: 'What data did the model use?', icon: 'ri-database-2-line' },
  ],
};

export const GENERAL_QUESTIONS = {
  zh: [
    { label: '你能做什么？', icon: 'ri-robot-line' },
    { label: '如何开始一次预测？', icon: 'ri-play-circle-line' },
    { label: '系统支持哪些灾种？', icon: 'ri-alert-line' },
    { label: '预测结果怎么解释？', icon: 'ri-bar-chart-2-line' },
    { label: '知识图谱有什么作用？', icon: 'ri-git-branch-line' },
  ],
  en: [
    { label: 'What can you do?', icon: 'ri-robot-line' },
    { label: 'How do I start a prediction?', icon: 'ri-play-circle-line' },
    { label: 'Which hazards does the system support?', icon: 'ri-alert-line' },
    { label: 'How are prediction results explained?', icon: 'ri-bar-chart-2-line' },
    { label: 'What does the knowledge graph do?', icon: 'ri-git-branch-line' },
  ],
};

function containsAny(text: string, keywords: string[]): boolean {
  return keywords.some((keyword) => text.includes(keyword));
}

function contextScoreLabel(context: ChatContext, lang: ChatLang): string {
  return scoreLabel(context, lang);
}

function contextCalibrationLabel(context: ChatContext, lang: ChatLang): string {
  return calibrationLabel(context, lang);
}

const GENERAL_KEYWORDS = {
  zh: {
    start: ['开始', '怎么用', '如何使用', '工作台', '发起'],
    hazards: ['灾种', '支持', '类型'],
    explain: ['解释', '图谱', '结果'],
  },
  en: {
    start: ['start', 'how to use', 'workspace', 'begin', 'create'],
    hazards: ['hazard', 'support', 'type'],
    explain: ['explain', 'graph', 'result'],
  },
};

export function generateGeneralResponse(userMessage: string, lang: ChatLang = 'zh'): string {
  const message = userMessage.toLowerCase().trim();
  const kw = GENERAL_KEYWORDS[lang];

  if (lang === 'en') {
    if (containsAny(message, kw.start)) {
      return 'Head to the **Prediction Workspace**, choose live prediction or 2025 historical replay, then pick a region, hazard, and one of the models the system actually supports. Historical replay currently only supports the 24-hour T+1 day model.';
    }
    if (containsAny(message, kw.hazards)) {
      return 'The system currently covers **extreme heat, flash flood, dust storm, and heavy rain**. The 2025 historical replay has heat, flash-flood, and dust-storm models; all four hazards have live HGB post-processing models using features aggregated from a third-party hourly forecast.';
    }
    if (containsAny(message, kw.explain)) {
      return 'The system splits explanation into four categories: real input indicators, Tree SHAP model attribution, versioned risk rules, and mechanism compatibility with historical analogies. The graph connects this evidence without passing off correlation or expert mechanisms as model causation.';
    }
    return "I'm the prediction explanation assistant. Without a specific prediction in context, I can only describe the system's capabilities; once you open a prediction's detail page, I'll reference that record's actual saved model, data source, score semantics, rules, and evidence.";
  }

  if (containsAny(message, kw.start)) {
    return '请进入**预测工作台**，先选择实时预测或2025历史回放，再选择区域、灾种和系统实际支持的模型。历史回放当前只支持24小时T+1日模型。';
  }
  if (containsAny(message, kw.hazards)) {
    return '系统当前覆盖**极端高温、山洪、沙尘暴和强降雨**。2025历史回放有高温、山洪和沙尘暴模型；四个灾种都有使用第三方逐小时预报聚合特征的实时HGB后处理模型。';
  }
  if (containsAny(message, kw.explain)) {
    return '系统把解释分为四类：真实输入指标、Tree SHAP模型归因、版本化风险规则、机制相容性与历史类比。图谱负责连接这些证据，不把相关性或专家机制冒充模型因果。';
  }
  return '我是预测解释助手。未关联具体预测时，我只介绍系统能力；进入预测详情后，我会引用该记录实际保存的模型、数据来源、分数语义、规则和证据。';
}

const CONTEXT_KEYWORDS = {
  zh: {
    credibility: ['可信', '信度', '靠谱', '准确', '不确定', '置信', '边界', '模糊'],
    score: ['分数', '概率', '为什么', '贡献', '因素'],
    risk: ['风险', '等级', '预警', '阈值', '怎么定'],
    history: ['历史', '以前', '类似', '案例'],
    mechanism: ['物理', '机制', '机理', '因果'],
    model: ['模型', '数据', '输入', '版本', '来源'],
  },
  en: {
    credibility: ['credib', 'reliab', 'accura', 'uncertain', 'confidence', 'boundary', 'ambigu'],
    score: ['score', 'probability', 'why', 'contribut', 'factor'],
    risk: ['risk', 'level', 'alert', 'warning', 'threshold', 'determined'],
    history: ['history', 'before', 'similar', 'case', 'precedent'],
    mechanism: ['physical', 'mechanism', 'causa'],
    model: ['model', 'data', 'input', 'version', 'source'],
  },
};

export function generateResponse(userMessage: string, context: ChatContext, lang: ChatLang = 'zh'): string {
  const message = userMessage.toLowerCase().trim();
  const score = `${(context.decisionScore * 100).toFixed(0)}/100`;
  const kw = CONTEXT_KEYWORDS[lang];

  if (lang === 'en') {
    if (containsAny(message, kw.credibility)) {
      return [
        `This result is **${contextScoreLabel(context, lang)} ${score}**, calibration status **${contextCalibrationLabel(context, lang)}**.`,
        `The heuristic ambiguity is **${(context.ambiguity * 100).toFixed(0)}/100 (${ambiguityLabel(context.ambiguity, lang)})**. It only reflects how close the model score is to the decision midpoint, not a +/- error or a statistical confidence interval.`,
        `The model is **${context.modelName} ${context.modelVersion}**, input tier **${context.dataTier}**. This result should therefore be used alongside subsequent updates and official warnings.`,
      ].join('\n\n');
    }

    if (containsAny(message, kw.score)) {
      const features = context.featureSummaries.length
        ? context.featureSummaries.map((item) => `- ${item}`).join('\n')
        : '- No verifiable Tree SHAP attribution for this record';
      return `This **${contextScoreLabel(context, lang)}** is **${score}**. The main local attributions from Tree SHAP on the model's raw log-odds scale are:\n${features}\n\nThese contributions explain the model output; they do not represent physical causation or probability points.`;
    }

    if (containsAny(message, kw.risk)) {
      const rules = context.triggeredRuleNames.length
        ? context.triggeredRuleNames.map((item) => `- ${item}`).join('\n')
        : '- No rules triggered';
      return `The current risk level is **${context.riskLevel}**. The risk policy maps this decision score, regional sensitivity, and indicator rules; the rules actually triggered are:\n${rules}\n\nThis is a risk decision, not an official warning issued directly by the model.`;
    }

    if (containsAny(message, kw.history)) {
      const events = context.similarEventSummaries.length
        ? context.similarEventSummaries.map((item) => `- ${item}`).join('\n')
        : '- No historical analog case meets the time/source constraints for this record';
      return `Historical analogy results saved for this prediction:\n${events}\n\nSimilar cases only indicate that the multi-dimensional weather background is close; they do not mean this case will necessarily produce the same impact.`;
    }

    if (containsAny(message, kw.mechanism)) {
      const mechanisms = context.mechanismNames.length
        ? context.mechanismNames.map((item) => `- ${item}`).join('\n')
        : '- No mechanism-compatibility result available for this record';
      return `The mechanism compatibility returned by the current knowledge package includes:\n${mechanisms}\n\nMechanism compatibility is the degree of agreement between expert knowledge and the current indicator state; it does not prove case-specific causation, and it is not Tree SHAP model attribution.`;
    }

    if (containsAny(message, kw.model)) {
      return `This run used **${context.modelName} ${context.modelVersion}**, data tier **${context.dataTier}**, forecast source **${context.forecastSource || '2025 historical indicator archive'}**, lead time **${context.leadTimeHours}h**. Prediction record ID: **${context.predictionId}**.`;
    }

    return `Current record: ${context.regionName} ${context.hazardLabel}, ${contextScoreLabel(context, lang)} **${score}**, risk level **${context.riskLevel}**. You can keep asking about model contributions, calibration status, risk rules, mechanisms, or historical cases.`;
  }

  if (containsAny(message, kw.credibility)) {
    return [
      `本次结果是**${contextScoreLabel(context, lang)} ${score}**，校准状态为**${contextCalibrationLabel(context, lang)}**。`,
      `启发式判别模糊度为 **${(context.ambiguity * 100).toFixed(0)}/100（${ambiguityLabel(context.ambiguity, lang)}）**。它只反映模型分数接近决策中点的程度，不是±误差或统计置信区间。`,
      `模型为 **${context.modelName} ${context.modelVersion}**，输入层级为 **${context.dataTier}**。因此该结果应与后续更新及官方预警共同使用。`,
    ].join('\n\n');
  }

  if (containsAny(message, kw.score)) {
    const features = context.featureSummaries.length
      ? context.featureSummaries.map((item) => `- ${item}`).join('\n')
      : '- 当前记录没有可验证的Tree SHAP归因';
    return `本次**${contextScoreLabel(context, lang)}**为 **${score}**。Tree SHAP在模型raw log-odds尺度上的主要局部归因为：\n${features}\n\n这些贡献解释模型输出，不代表物理因果或概率百分点。`;
  }

  if (containsAny(message, kw.risk)) {
    const rules = context.triggeredRuleNames.length
      ? context.triggeredRuleNames.map((item) => `- ${item}`).join('\n')
      : '- 没有规则命中';
    return `当前风险等级为 **${context.riskLevel}**。风险政策使用本次决策分数、区域敏感性和指标规则进行映射；实际命中的规则是：\n${rules}\n\n这是一项风险决策，不是模型直接输出的官方预警。`;
  }

  if (containsAny(message, kw.history)) {
    const events = context.similarEventSummaries.length
      ? context.similarEventSummaries.map((item) => `- ${item}`).join('\n')
      : '- 当前记录没有满足时间与来源约束的历史类比案例';
    return `当前预测保存的历史类比结果：\n${events}\n\n相似案例只表示多维天气背景接近，不表示本次一定产生相同影响。`;
  }

  if (containsAny(message, kw.mechanism)) {
    const mechanisms = context.mechanismNames.length
      ? context.mechanismNames.map((item) => `- ${item}`).join('\n')
      : '- 当前记录没有可用的机制相容性结果';
    return `当前知识包返回的机制相容性包括：\n${mechanisms}\n\n机制相容性是专家知识与当前指标状态的一致程度，不证明个例因果，也不是Tree SHAP模型归因。`;
  }

  if (containsAny(message, kw.model)) {
    return `本次使用 **${context.modelName} ${context.modelVersion}**，数据层级为 **${context.dataTier}**，预报来源为 **${context.forecastSource || '2025历史指标归档'}**，预报时效 **${context.leadTimeHours}小时**。预测记录ID为 **${context.predictionId}**。`;
  }

  return `当前记录：${context.regionName} ${context.hazardLabel}，${contextScoreLabel(context, lang)} **${score}**，风险等级 **${context.riskLevel}**。你可以继续询问模型贡献、校准状态、风险规则、机制或历史案例。`;
}

export function buildChatContext(prediction: PredictionResult): ChatContext {
  return {
    hazardLabel: prediction.hazardLabel,
    regionName: prediction.regionName,
    riskLevel: prediction.riskLabel,
    decisionScore: prediction.decisionScore,
    scoreSemantics: prediction.scoreSemantics,
    calibrationMethod: prediction.calibrationMethod,
    isCalibrated: prediction.isCalibrated,
    ambiguity: prediction.ambiguity,
    ambiguityMethod: prediction.ambiguityMethod,
    modelName: prediction.modelName,
    modelVersion: prediction.modelVersion,
    leadTimeHours: prediction.leadTimeHours,
    dataTier: prediction.dataTier,
    forecastSource: prediction.forecastSource,
    featureSummaries: prediction.features.slice(0, 5).map((feature) => (
      `${feature.featureLabel}: SHAP ${feature.contribution >= 0 ? '+' : ''}${feature.contribution.toFixed(3)}`
    )),
    triggeredRuleNames: prediction.ruleHits.filter((rule) => rule.met).map((rule) => rule.ruleName),
    mechanismNames: prediction.mechanisms.map((mechanism) => mechanism.pathName),
    similarEventSummaries: prediction.similarEvents.map((event) => `${event.date} ${event.region}：${event.description}`),
    predictionId: prediction.predictionId,
  };
}
