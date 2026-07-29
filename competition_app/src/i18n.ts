import type { Locale } from "./types";

const copy = {
  zh: {
    console: "预警演练台",
    analysis: "事件诊断",
    evidence: "证据网络",
    assistant: "决策简报",
    reports: "提交材料",
    archive: "旧版归档",
    historical: "历史演练",
    boundary: "2025历史数据 · 非业务预警",
    selectTask: "历史预警演练",
    selectTaskLead: "选择城市、日期和灾种，使用前一日指标运行一次可审计的风险评估。",
    run: "运行风险评估",
    running: "正在读取模型与指标",
    city: "城市",
    targetDate: "目标日期",
    hazard: "灾种",
    scenarios: "核验场景",
    recent: "最近演练",
    noRun: "运行一个场景后，这里将生成风险简报。",
    riskBrief: "风险简报",
    probability: "模型风险",
    ruleScore: "规则风险",
    consistency: "一致性检查",
    inputDate: "输入截止日",
    modelSpread: "模型分歧",
    openAnalysis: "打开完整分析",
    archiveMode: "归档模式",
    archiveMessage: "本地数据或模型不完整，自由预测已停用；固定报告和历史归档仍可查看。",
    analysisTitle: "事件诊断",
    analysisLead: "在同一视图核对概率场、规则风险、模型分歧和验证指标。",
    layerProbability: "模型概率",
    layerRule: "规则风险",
    layerUncertainty: "不确定性",
    evidenceTitle: "证据网络",
    assistantTitle: "决策简报",
    reportsTitle: "提交材料",
    generateReport: "生成双语报告",
    generateCap: "生成 CAP Exercise",
    ask: "分析当前结果",
    send: "发送",
    noSelectedRun: "请先在预警演练台运行或选择一条历史记录。",
    localDataReady: "本地数据就绪",
    archiveModeShort: "归档模式",
    datasetYear: "数据集 / 2025",
    currentExercise: "当前演练",
    consoleEyebrow: "预警工作流 / 01",
    analysisEyebrow: "事件诊断 / 02",
    evidenceEyebrow: "证据网络 / 03",
    assistantEyebrow: "决策简报 / 04",
    reportsEyebrow: "制品中心 / 05",
    taskControl: "任务控制",
    curatedAudited: "精选 / 已核验",
    noLocalRuns: "尚无本地演练记录",
    noActiveExercise: "尚未选择演练",
    saudiGridField: "沙特网格场",
    loading: "载入中",
    readingField: "正在读取历史场",
    localCache: "本地缓存",
    modelDerived: "模型计算",
    reliability: "可靠性指标",
    fixedThreshold: "固定阈值",
    interpretationBoundary: "解读边界",
    inputIndicators: "输入指标",
    crossCheck: "交叉复核",
    model: "模型",
    rule: "规则",
    eventSubgraph: "事件子图",
    nodes: "节点",
    edges: "关系",
    indicatorNode: "指标",
    mechanismNode: "机制",
    hazardNode: "灾种",
    citationNode: "文献",
    nodeInspector: "节点核验",
    relationsInView: "图中关系",
    historicalExerciseLabel: "历史演练",
    optionalFollowup: "可选追问",
    deepseekAvailable: "DeepSeek 可用",
    deterministicTemplate: "确定性模板",
    currentRunArtifacts: "当前演练制品",
    ready: "可生成",
    noRunShort: "无演练",
    documentLibrary: "文档资料库",
    items: "项",
    runFailed: "风险评估运行失败，请检查本地服务状态。",
    fieldFailed: "历史网格场读取失败。",
    reportKindResearch: "研究报告",
    reportKindVerification: "核验报告",
    reportKindArchive: "历史归档",
  },
  en: {
    console: "Warning console",
    analysis: "Event diagnostics",
    evidence: "Evidence network",
    assistant: "Decision brief",
    reports: "Submission",
    archive: "Legacy archive",
    historical: "Historical Exercise",
    boundary: "2025 historical data · Not an operational warning",
    selectTask: "Historical warning exercise",
    selectTaskLead: "Choose a city, date and hazard to run one auditable assessment from prior-day indicators.",
    run: "Run risk assessment",
    running: "Reading models and indicators",
    city: "City",
    targetDate: "Target date",
    hazard: "Hazard",
    scenarios: "Verified scenarios",
    recent: "Recent exercises",
    noRun: "Run a scenario to generate a risk bulletin here.",
    riskBrief: "Risk bulletin",
    probability: "Model risk",
    ruleScore: "Rule risk",
    consistency: "Consistency",
    inputDate: "Input cutoff",
    modelSpread: "Model spread",
    openAnalysis: "Open full analysis",
    archiveMode: "Archive mode",
    archiveMessage: "Local data or models are incomplete. Free prediction is disabled; fixed reports and archives remain available.",
    analysisTitle: "Event diagnostics",
    analysisLead: "Review the probability field, rule risk, model spread and verification metrics together.",
    layerProbability: "Model probability",
    layerRule: "Rule risk",
    layerUncertainty: "Uncertainty",
    evidenceTitle: "Evidence network",
    assistantTitle: "Decision brief",
    reportsTitle: "Submission artifacts",
    generateReport: "Generate bilingual report",
    generateCap: "Generate CAP Exercise",
    ask: "Analyze this result",
    send: "Send",
    noSelectedRun: "Run or select an exercise in the warning console first.",
    localDataReady: "Local data ready",
    archiveModeShort: "Archive mode",
    datasetYear: "Dataset / 2025",
    currentExercise: "Current exercise",
    consoleEyebrow: "Warning workflow / 01",
    analysisEyebrow: "Event diagnostics / 02",
    evidenceEyebrow: "Evidence network / 03",
    assistantEyebrow: "Decision brief / 04",
    reportsEyebrow: "Artifact library / 05",
    taskControl: "Task control",
    curatedAudited: "Curated / audited",
    noLocalRuns: "No local exercises yet",
    noActiveExercise: "No active exercise",
    saudiGridField: "Saudi grid field",
    loading: "Loading",
    readingField: "Reading historical field",
    localCache: "Local cache",
    modelDerived: "Model derived",
    reliability: "Reliability",
    fixedThreshold: "Fixed threshold",
    interpretationBoundary: "Interpretation boundary",
    inputIndicators: "Input indicators",
    crossCheck: "Cross-check",
    model: "Model",
    rule: "Rule",
    eventSubgraph: "Event subgraph",
    nodes: "nodes",
    edges: "edges",
    indicatorNode: "Indicator",
    mechanismNode: "Mechanism",
    hazardNode: "Hazard",
    citationNode: "Citation",
    nodeInspector: "Node inspector",
    relationsInView: "Relations in view",
    historicalExerciseLabel: "Historical exercise",
    optionalFollowup: "Optional follow-up",
    deepseekAvailable: "DeepSeek available",
    deterministicTemplate: "Deterministic template",
    currentRunArtifacts: "Current run artifacts",
    ready: "Ready",
    noRunShort: "No run",
    documentLibrary: "Document library",
    items: "items",
    runFailed: "The risk assessment failed. Check the local service status.",
    fieldFailed: "The historical grid field could not be loaded.",
    reportKindResearch: "Research report",
    reportKindVerification: "Verification report",
    reportKindArchive: "Legacy archive",
  },
} as const;

export type CopyKey = keyof typeof copy.zh;
export const t = (locale: Locale, key: CopyKey) => copy[locale][key];

export const hazardLabel = (locale: Locale, hazard: string) => {
  const labels: Record<string, [string, string]> = {
    heatwave: ["高温热浪", "Heatwave"],
    flash_flood: ["山洪风险", "Flash-flood risk"],
    dust_storm: ["沙尘暴", "Dust storm"],
  };
  return labels[hazard]?.[locale === "zh" ? 0 : 1] || hazard;
};

export const cityLabel = (locale: Locale, city: string) => {
  const labels: Record<string, string> = {
    Jeddah: "吉达", Mecca: "麦加", Riyadh: "利雅得", Jizan: "吉赞",
    Dammam: "达曼", Taif: "塔伊夫", Medina: "麦地那", Abha: "艾卜哈",
  };
  return locale === "zh" ? labels[city] || city : city;
};

const humanize = (value: string) => value.replaceAll("_", " ");

export const riskLevelLabel = (locale: Locale, level?: string) => {
  if (!level) return locale === "zh" ? "不可用" : "Unavailable";
  const labels: Record<string, [string, string]> = {
    low: ["低风险", "Low"],
    moderate: ["中等风险", "Moderate"],
    elevated: ["较高风险", "Elevated"],
    high: ["高风险", "High"],
    emergency: ["紧急风险", "Emergency"],
  };
  return labels[level]?.[locale === "zh" ? 0 : 1] || (locale === "zh" ? "待复核" : humanize(level));
};

export const consistencyLabel = (locale: Locale, value?: string) => {
  if (!value) return locale === "zh" ? "不可用" : "Unavailable";
  const labels: Record<string, [string, string]> = {
    consistent_high: ["高风险一致", "Consistent high risk"],
    consistent_low: ["低风险一致", "Consistent low risk"],
    model_higher_than_detection: ["模型高于规则", "Model higher than rules"],
    detection_higher_than_model: ["规则高于模型", "Rules higher than model"],
    unavailable: ["不可用", "Unavailable"],
  };
  return labels[value]?.[locale === "zh" ? 0 : 1] || (locale === "zh" ? "需要人工复核" : humanize(value));
};

export const indicatorLabel = (locale: Locale, indicator: string) => {
  const labels: Record<string, [string, string]> = {
    daily_precip_total: ["日总降水量", "Total daily precipitation"],
    daily_convective_precip: ["日对流降水量", "Convective precipitation"],
    daily_large_scale_precip: ["日大尺度降水量", "Large-scale precipitation"],
    daily_precip_anomaly: ["日降水距平", "Daily precipitation anomaly"],
    t2m_c: ["2米气温", "2 m air temperature"],
    tmax_c: ["日最高气温", "Daily maximum temperature"],
    tmin_c: ["日最低气温", "Daily minimum temperature"],
    heat_index_c: ["体感温度", "Heat index"],
    vpd_kpa: ["饱和水汽压差", "Vapour pressure deficit"],
    cape: ["对流有效位能", "Convective available potential energy"],
    pwat: ["可降水量", "Precipitable water"],
    ivt: ["整层水汽输送", "Integrated vapour transport"],
    wind850_speed: ["850百帕风速", "850 hPa wind speed"],
    wind_shear_850_200: ["850—200百帕风切变", "850–200 hPa wind shear"],
    t2m_anomaly_c: ["2米气温距平", "2 m temperature anomaly"],
    tmax_anomaly_c: ["最高气温距平", "Maximum temperature anomaly"],
    sst_celsius: ["海表温度", "Sea-surface temperature"],
    flash_flood_risk: ["山洪规则风险", "Flash-flood rule risk"],
    heatwave_day_flag: ["热浪日标记", "Heatwave-day flag"],
    heatwave_duration_days: ["热浪持续天数", "Heatwave duration"],
    wind10_speed: ["10米风速", "10 m wind speed"],
    dewpoint_depression_c: ["露点差", "Dew-point depression"],
    dust_storm_rule_score: ["沙尘规则风险", "Dust-storm rule risk"],
  };
  return labels[indicator]?.[locale === "zh" ? 0 : 1] || (locale === "zh" ? `指标 ${indicator}` : humanize(indicator));
};

export const mechanismLabel = (locale: Locale, mechanism: string) => {
  const labels: Record<string, [string, string]> = {
    ARST: ["活跃红海槽（ARST）", "Active Red Sea Trough (ARST)"],
    moisture_transport: ["水汽输送", "Moisture transport"],
    subtropical_high: ["副热带高压", "Subtropical high"],
    thermal_low: ["热低压", "Thermal low"],
    orographic_lift: ["地形抬升", "Orographic lift"],
  };
  return labels[mechanism]?.[locale === "zh" ? 0 : 1] || (locale === "zh" ? `机制 ${mechanism}` : humanize(mechanism));
};

export const mechanismDescription = (locale: Locale, mechanism: string, original: string) => {
  if (locale === "en") return original;
  const descriptions: Record<string, string> = {
    ARST: "活跃红海槽可在红海沿岸形成低层辐合，是图谱中人工维护的强降水机制断言。",
    moisture_transport: "来自红海或阿拉伯海的水汽输送可为强降水提供水汽条件，是图谱中的人工机制断言。",
    subtropical_high: "副热带或大陆高压可造成下沉增温与持续高温，是图谱中的人工机制断言。",
    thermal_low: "阿拉伯半岛热低压与干热、沙尘活动有关，是图谱中的人工机制断言。",
    orographic_lift: "气流受汉志与阿西尔山地抬升可增强降水，是图谱中的人工机制断言。",
  };
  return descriptions[mechanism] || `${mechanismLabel(locale, mechanism)}是人工维护的领域机制断言，详细原文保留在证据源中。`;
};

export const evidenceStatusLabel = (locale: Locale, status?: string) => {
  const normalized = (status || "").toLowerCase();
  if (locale === "en") return status ? humanize(status) : "Scope limited";
  if (normalized === "run result") return "运行结果";
  if (normalized === "observed") return "已观测";
  if (normalized === "grounded") return "有文献依据";
  if (normalized.includes("review")) return "待人工核验";
  if (normalized.includes("verified")) return "已核验";
  return "适用范围有限";
};

export const evidenceBoundary = (locale: Locale, original: string) => locale === "zh"
  ? "机制关系为人工维护的领域断言；文献记录仅表示本地证据匹配与有限核验。图谱不参与模型训练或风险评分。"
  : original;

export const ruleNote = (locale: Locale, consistency?: string) => {
  const label = consistencyLabel(locale, consistency);
  return locale === "zh"
    ? `模型结果与规则引擎的对照结论为“${label}”。两者提供相互复核，不改变模型原始概率。`
    : `The model-to-rule comparison is “${label}”. The cross-check does not alter the original model probability.`;
};

export const reportKindLabel = (locale: Locale, kind: string) => {
  const keys = {
    research: "reportKindResearch",
    verification: "reportKindVerification",
    archive: "reportKindArchive",
  } as const;
  return t(locale, keys[kind as keyof typeof keys] || "reportKindArchive");
};
