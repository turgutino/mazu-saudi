import type { PredictionResult } from '@/mocks/predictions';

export interface ChatMessage {
  role: 'user' | 'agent';
  content: string;
  timestamp: number;
}

export interface ChatContext {
  hazardLabel: string;
  regionName: string;
  riskLevel: string;
  probability: number;
  calibratedProbability: number;
  uncertainty: number;
  modelName: string;
  modelVersion: string;
  leadTimeHours: number;
  featureNames: string[];
  triggeredRuleCount: number;
  totalRuleCount: number;
  mechanismCount: number;
  similarEventCount: number;
  predictionId: string;
}

export const SUGGESTED_QUESTIONS = [
  { label: '这个预测可信度怎么样？', icon: 'ri-shield-check-line' },
  { label: '为什么概率这么高？', icon: 'ri-question-line' },
  { label: '历史上发生过类似事件吗？', icon: 'ri-history-line' },
  { label: '风险等级是怎么定的？', icon: 'ri-alert-line' },
  { label: '物理机制是什么？', icon: 'ri-git-branch-line' },
  { label: '模型用了哪些数据？', icon: 'ri-database-2-line' },
];

export const GENERAL_QUESTIONS = [
  { label: '你能做什么？', icon: 'ri-robot-line' },
  { label: '如何开始一次预测？', icon: 'ri-play-circle-line' },
  { label: '系统支持哪些灾种？', icon: 'ri-alert-line' },
  { label: '预测结果怎么解释？', icon: 'ri-bar-chart-2-line' },
  { label: '知识图谱有什么作用？', icon: 'ri-git-branch-line' },
  { label: '模型版本和审计怎么保证？', icon: 'ri-shield-check-line' },
];

function containsAny(text: string, keywords: string[]): boolean {
  return keywords.some((kw) => text.includes(kw));
}

export function generateGeneralResponse(userMessage: string): string {
  const msg = userMessage.toLowerCase().trim();

  if (containsAny(msg, ['你好', 'hi', 'hello', '嗨', '在吗', '做什么', '能做什么', '功能', '介绍一下', '你是谁'])) {
    return [
      '你好！我是**预测智能体助手**，一个由预测模型产生数值结果、智能体负责编排和解释的极端天气预测系统。',
      '',
      '**我能帮你做的事：**',
      '- 在工作台选择区域和灾种，发起预测',
      '- 解读预测结果：概率、风险等级、不确定性',
      '- 解释模型判断：SHAP 特征贡献、命中规则、物理机制',
      '- 查询相似历史事件',
      '- 在知识图谱中追踪推理证据链',
      '',
      '要开始使用，你可以先去**预测仪表盘**查看最近的预测记录，或者去**预测工作台**发起一次新预测。',
      '',
      '关于预测的可靠性：我不会编造数字 — 概率来自训练好的模型，规则来自业务阈值配置，解释来自 SHAP 分析和专家知识，图谱保存完整的推理证据。所有结果都可追溯、可审计。',
    ].join('\n');
  }

  if (containsAny(msg, ['开始', '预测', '工作台', '发起', '新建', '怎么用', '如何使用'])) {
    return [
      '发起一次预测非常简单，去**预测工作台**（导航栏 → 预测工作台），按以下步骤操作：',
      '',
      '**第 1 步**：选择目标区域（例如：吉赞、吉达、利雅得）',
      '**第 2 步**：选择灾种类型（暴雨/山洪、极端高温、沙尘暴等）',
      '**第 3 步**：选择预报时效（6h、12h、24h、48h）',
      '**第 4 步**：选择预测模型（集成模型、XGBoost、深度学习等）',
      '**第 5 步**：确认后智能体会自动编排执行',
      '',
      '完成后你会看到一个完整的预测结果页面，包含概率、解释和图谱。',
      '',
      '去导航栏点击「预测工作台」就能开始！',
    ].join('\n');
  }

  if (containsAny(msg, ['灾种', '什么灾', '支持', '类型', '哪些'])) {
    return [
      '系统目前支持的极端天气灾种：',
      '',
      '**暴雨 / 山洪** — 基于 CAPE、可降水量、降水预报和水汽输送指标',
      '**极端高温** — 基于 2m 气温、500hPa 位势高度、土壤湿度等指标',
      '**沙尘暴** — 基于 10m 风速、土壤湿度、能见度等指标',
      '**强对流** — 基于 CAPE、风切变、抬升指数等指标',
      '',
      '每个灾种都有独立的预测模型、风险规则和解释链。建议第一版先聚焦暴雨/山洪和极端高温。',
    ].join('\n');
  }

  if (containsAny(msg, ['解释', '怎么理解', '结果', '怎么看'])) {
    return [
      '预测结果有五种解释维度，互相补充：',
      '',
      '**特征贡献** — 回答「模型为什么给出这个概率？」通过 SHAP 方法计算每个输入变量对预测的贡献，展示条形图',
      '**命中规则** — 回答「为什么发出这个风险等级？」展示哪些业务规则被触发、阈值是多少',
      '**物理机制** — 回答「气象上为什么可能发生？」用专家知识构建因果链，是支持机制而非模型内部推理',
      '**相似事件** — 回答「历史上发生过类似事件吗？」在历史库中检索特征相似的事件',
      '**解释图谱** — 以上所有内容的可视化证据链，可拖拽缩放探索',
      '',
      '进入任意预测结果页面，顶部有五个 Tab 可以切换查看。',
    ].join('\n');
  }

  if (containsAny(msg, ['图谱', '知识图谱', '证据', '图', '可视化'])) {
    return [
      '**解释证据图谱**是系统的核心可视化工具，建模了从数据到预警的完整推理链：',
      '',
      '**节点类型**：ForecastCase → Prediction → FeatureAttribution → RuleHit → RiskAssessment → Warning',
      '**三大功能**：',
      '- 分组折叠/展开：按核心流程、特征贡献、风险规则、物理机制等分组管理',
      '- 时间轴回放：逐步骤展示推理过程（7 个步骤）',
      '- 节点跳转：从图谱节点直接跳到对应的解释详情 Tab',
      '',
      '图谱不仅展示领域知识结构，还保存每次真实预测的上下文 — 这是可审计、可复现的关键。',
      '',
      '进入任意预测结果页面，点击「查看图谱」按钮即可打开。',
    ].join('\n');
  }

  if (containsAny(msg, ['模型', '版本', '审计', '可追溯', '复现', '数据'])) {
    return [
      '关于系统的**可审计和可复现设计**：',
      '',
      '**输入数据哈希** — 每次预测保存 inputHash，证明使用了哪批数据',
      '**模型版本** — 每次预测带 modelVersion，模型更新后仍可复现历史预测',
      '**Prediction vs RiskAssessment** — 模型结果和业务决策严格分离，修改预警标准不需要重新训练模型',
      '**AgentRun 日志** — 每次智能体运行记录调用了哪些工具、产生哪些预测',
      '**解释证据图谱** — 完整保存特征贡献、命中规则、机制链和相似事件',
      '',
      '这些设计确保系统满足气象业务的可追溯性要求。',
    ].join('\n');
  }

  // Default general response
  return [
    '关于你的问题，我目前处于通用助手模式（未关联到具体的预测结果）。',
    '',
    '你可以试试问我：',
    '- "你能做什么？"',
    '- "如何开始一次预测？"',
    '- "系统支持哪些灾种？"',
    '- "预测结果怎么解释？"',
    '',
    '或者去**预测仪表盘**查看最近的预测，去**预测工作台**发起新预测。进入具体的预测结果页面后，我就能提供该预测的详细分析了。',
  ].join('\n');
}

export function generateResponse(userMessage: string, context: ChatContext): string {
  const msg = userMessage.toLowerCase().trim();

  // Credibility / uncertainty
  if (containsAny(msg, ['可信', '信度', '靠谱', '准确', '不确定', '置信'])) {
    const uncertaintyDesc = context.uncertainty < 0.12 ? '低' : context.uncertainty < 0.2 ? '中等' : '较高';
    return [
      `关于 ${context.regionName} ${context.hazardLabel} 预测的可信度分析：`,
      ``,
      `**校准后概率**为 ${(context.calibratedProbability * 100).toFixed(0)}%（原始概率 ${(context.probability * 100).toFixed(0)}%），经过概率校准后更接近真实发生频率。`,
      ``,
      `**模型不确定性**为 ±${(context.uncertainty * 100).toFixed(0)}%，属于${uncertaintyDesc}不确定性水平。不确定性来源于：`,
      `- 预报时效较长（${context.leadTimeHours} 小时），随时间推移不确定性会降低`,
      `- 单次预测存在随机波动，集成模型（${context.modelName} ${context.modelVersion}）通过多模型平均已部分缓解`,
      `- 地形复杂区域（${context.regionName}）的局地效应难以完全捕捉`,
      ``,
      `综合来看，这是一个可信度${uncertaintyDesc === '低' ? '较高' : '一般'}的预测，建议结合后续更新和官方预警综合判断。`,
    ].join('\n');
  }

  // Probability explanation
  if (containsAny(msg, ['概率', '为什么', '原因', '因素', '贡献', '高', '升高', '上升'])) {
    return [
      `${context.hazardLabel} 概率达到 ${(context.calibratedProbability * 100).toFixed(0)}% 的**主要驱动因素**：`,
      ``,
      ...context.featureNames.slice(0, 4).map((name, i) => {
        const contributions = ['CAPE 大幅高于气候平均值', '大气可降水量异常偏高', '日降水预报超过阈值', '850 hPa 水汽输送显著增强'];
        return `${i + 1}. **${name}**：${contributions[i] || '正向贡献'}，推动概率上升`;
      }),
      ``,
      `这些因子共同指向一个**对流不稳定 + 充足水汽**的配置，是 ${context.hazardLabel} 发生的典型前兆信号。`,
      ``,
      `需要注意的是，特征贡献是通过 SHAP 方法计算的，反映的是"模型认为哪些变量重要"，而非物理因果。如果你对某个特征的具体贡献值好奇，可以切换到「特征贡献」Tab 查看完整的 SHAP 条形图。`,
    ].join('\n');
  }

  // Historical events
  if (containsAny(msg, ['历史', '以前', '过去', '类似', '相似', '发生过', '记录'])) {
    return [
      `基于当前预测的特征向量，在历史事件库中检索到 **${context.similarEventCount} 个相似事件**：`,
      ``,
      `- **2024年8月 吉赞山洪**（相似度 91%）：CAPE 和可降水量指标与当前预测高度吻合，该次事件导致严重山洪。`,
      `- **2023年7月 吉达山洪**（相似度 78%）：虽然地理位置不同，但气象配置有显著相似性。`,
      ``,
      `相似度计算基于特征空间的欧氏距离，综合考虑了 CAPE、可降水量、降水预报、水汽输送等多个维度。`,
      ``,
      `⚠️ **重要提示**：相似事件仅提供参考，不代表本次预测一定发展为同等强度的事件。每个气象过程都有其独特性。`,
      ``,
      `要查看更详细的历史事件信息，可以切换到「相似事件」Tab。`,
    ].join('\n');
  }

  // Risk level
  if (containsAny(msg, ['风险', '等级', '预警', '橙色', '红色', '怎么定', '为什么发', '阈值'])) {
    return [
      `${context.regionName} ${context.hazardLabel} 风险等级定为 **${context.riskLevel}**，基于以下决策过程：`,
      ``,
      `**第一步：模型预测**`,
      `- 校准后概率 ${(context.calibratedProbability * 100).toFixed(0)}%，超过 ${context.riskLevel.includes('橙') ? '橙色阈值 70%' : '相关风险阈值'}`,
      ``,
      `**第二步：规则匹配**`,
      `- ${context.triggeredRuleCount}/${context.totalRuleCount} 条风险规则被命中`,
      `- 涉及的规则包括：降水阈值规则、区域敏感性规则、强对流阈值规则`,
      ``,
      `**第三步：区域特征**`,
      `- ${context.regionName} 属于山洪高敏感区域，地形和排水条件使风险进一步升高`,
      ``,
      `**第四步：综合研判**`,
      `- 多条规则同时命中 + 高概率 + 敏感区域 → 输出橙色预警`,
      ``,
      `风险等级是模型概率 + 业务规则 + 区域背景的综合结果，不是模型直接给出的。这样设计是为了以后修改预警标准时不需要重新训练模型。`,
    ].join('\n');
  }

  // Physical mechanisms
  if (containsAny(msg, ['物理', '机制', '机理', '过程', '因果', '为什么会发生', '怎么发生'])) {
    return [
      `从气象物理角度看，${context.regionName} ${context.hazardLabel} 的发生机制涉及 **${context.mechanismCount} 条物理路径**：`,
      ``,
      `**路径一：水汽-对流路径**`,
      `高可降水量 → 水汽供应充足 → CAPE 升高 → 对流不稳定增强 → 强降水概率上升`,
      ``,
      `**路径二：地形抬升路径**`,
      `${context.regionName} 地形特征 → 气流遇地形抬升 → 触发对流 → 局地降水增强`,
      ``,
      `这些物理机制是专家基于气象学知识构建的"支持机制"，展示的是气象上可能发生的因果链，而不是模型内部的真实推理过程。`,
      ``,
      `模型的内部推理通过 SHAP 特征贡献来体现（见「特征贡献」Tab），物理机制则帮助人类理解"为什么在气象上是合理的"。两者互相补充。`,
    ].join('\n');
  }

  // Model / data
  if (containsAny(msg, ['模型', '数据', '什么模型', '用了什么', '算法', '训练', '输入'])) {
    return [
      `本次预测使用的模型信息：`,
      ``,
      `**模型**：${context.modelName} ${context.modelVersion}`,
      `- 这是一个多模型集成的预测系统`,
      `- 集成了 XGBoost、LightGBM 等梯度提升模型`,
      `- 通过加权平均融合多个模型的输出，提升稳定性和准确性`,
      ``,
      `**输入数据（${context.leadTimeHours} 小时预报时效）**：`,
      `- ERA5 再分析大气廓线数据`,
      `- 数值模式预报场（ECMWF / GFS）`,
      `- ${context.regionName} 地形和行政区划`,
      `- 历史极端天气事件标注`,
      ``,
      `**输出**：${context.hazardLabel} 发生概率、特征贡献、风险等级`,
      ``,
      `预测结果带有 predictionId（${context.predictionId}），可以追溯完整的输入数据哈希和模型版本，确保可复现和可审计。`,
    ].join('\n');
  }

  // Greetings
  if (containsAny(msg, ['你好', 'hi', 'hello', '嗨', '在吗'])) {
    return [
      `你好！我是预测智能体助手，负责解释和分析 ${context.regionName} ${context.hazardLabel} 预测结果。`,
      ``,
      `当前预测概况：`,
      `- 校准后概率 **${(context.calibratedProbability * 100).toFixed(0)}%**`,
      `- 风险等级 **${context.riskLevel}**`,
      `- 预报时效 **${context.leadTimeHours} 小时**`,
      ``,
      `你可以问我关于特征贡献、风险规则、历史事件、物理机制等方面的问题，也可以点击下方的快捷提问。`,
    ].join('\n');
  }

  // Default: helpful response
  return [
    `关于「${userMessage}」，我理解你想了解 ${context.regionName} ${context.hazardLabel} 预测中的相关内容。`,
    ``,
    `以下是当前预测的关键信息：`,
    `- ${context.hazardLabel} 概率：${(context.calibratedProbability * 100).toFixed(0)}%（校准后）`,
    `- 风险等级：${context.riskLevel}`,
    `- 命中规则：${context.triggeredRuleCount}/${context.totalRuleCount}`,
    `- ${context.mechanismCount} 条物理机制路径`,
    `- ${context.similarEventCount} 个相似历史事件`,
    ``,
    `你可以试试问我以下问题：`,
    `- "这个预测可信度怎么样？"`,
    `- "历史上发生过类似事件吗？"`,
    `- "风险等级是怎么定的？"`,
    ``,
    `或者切换到页面上的不同 Tab 查看详细的可视化解释。`,
  ].join('\n');
}

export function buildChatContext(prediction: PredictionResult): ChatContext {
  return {
    hazardLabel: prediction.hazardLabel,
    regionName: prediction.regionName,
    riskLevel: prediction.riskLevel,
    probability: prediction.probability,
    calibratedProbability: prediction.calibratedProbability,
    uncertainty: prediction.uncertainty,
    modelName: prediction.modelName,
    modelVersion: prediction.modelVersion,
    leadTimeHours: prediction.leadTimeHours,
    featureNames: prediction.features.map((f) => f.featureLabel),
    triggeredRuleCount: prediction.ruleHits.filter((r) => r.met).length,
    totalRuleCount: prediction.ruleHits.length,
    mechanismCount: prediction.mechanisms.length,
    similarEventCount: prediction.similarEvents.length,
    predictionId: prediction.predictionId,
  };
}