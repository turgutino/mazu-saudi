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
