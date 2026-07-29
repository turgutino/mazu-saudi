import type { Locale } from "./types";

const copy = {
  zh: {
    console: "预警演练台",
    analysis: "事件分析",
    evidence: "证据图谱",
    assistant: "决策简报",
    reports: "报告中心",
    archive: "旧版归档",
    historical: "历史演练",
    boundary: "2025历史数据 · 非业务预警",
    selectTask: "构建一次可审计的历史预警任务",
    selectTaskLead: "选择目标城市、日期和灾种。系统只使用前一日可获得指标。",
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
    analysisTitle: "一次预测，不只看一个概率",
    analysisLead: "并列查看模型、规则、可靠性和数据边界。",
    layerProbability: "模型概率",
    layerRule: "规则风险",
    layerUncertainty: "不确定性",
    evidenceTitle: "解释必须有来源，也必须暴露边界",
    assistantTitle: "把演练结果变成一份决策简报",
    reportsTitle: "从应用结果到可提交材料",
    generateReport: "生成双语报告",
    generateCap: "生成 CAP Exercise",
    ask: "分析当前结果",
    send: "发送",
    noSelectedRun: "请先在预警演练台运行或选择一条历史记录。",
  },
  en: {
    console: "Warning console",
    analysis: "Event analysis",
    evidence: "Evidence graph",
    assistant: "Decision brief",
    reports: "Report center",
    archive: "Legacy archive",
    historical: "Historical Exercise",
    boundary: "2025 historical data · Not an operational warning",
    selectTask: "Build one auditable historical warning task",
    selectTaskLead: "Choose a target city, date and hazard. Only prior-day indicators are used.",
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
    analysisTitle: "A forecast is more than one probability",
    analysisLead: "Read model, rules, reliability and evidence boundaries together.",
    layerProbability: "Model probability",
    layerRule: "Rule risk",
    layerUncertainty: "Uncertainty",
    evidenceTitle: "Every explanation needs a source and a boundary",
    assistantTitle: "Turn the exercise result into a decision brief",
    reportsTitle: "From application result to submission artifact",
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
