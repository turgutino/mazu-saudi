import { createContext, useContext, useEffect, useMemo, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";
import { Link, NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation } from "d3-force";
import { quadtree } from "d3-quadtree";
import { api } from "./api";
import {
  cityLabel,
  consistencyLabel,
  evidenceBoundary,
  evidenceStatusLabel,
  hazardLabel,
  indicatorLabel,
  mechanismDescription,
  mechanismLabel,
  reportKindLabel,
  riskLevelLabel,
  ruleNote,
  t,
} from "./i18n";
import type { Config, FieldData, FieldLayer, Health, Locale, OntologyEdge, OntologyGraph, OntologyNode, ReportItem, Run, Scenario } from "./types";
import agentExamples from "./data/agentExamples.json";

type AppState = {
  locale: Locale;
  setLocale: (value: Locale) => void;
  health: Health | null;
  config: Config | null;
  scenarios: Scenario[];
  runs: Run[];
  selectedRun: Run | null;
  setSelectedRun: (run: Run | null) => void;
  refreshRuns: () => Promise<void>;
};

const Context = createContext<AppState | null>(null);
const useApp = () => {
  const value = useContext(Context);
  if (!value) throw new Error("App context unavailable");
  return value;
};

function AppProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => (localStorage.getItem("mazu-locale") as Locale) || "zh");
  const [health, setHealth] = useState<Health | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRun, setSelectedRunState] = useState<Run | null>(null);

  const refreshRuns = async () => {
    const items = await api.runs();
    setRuns(items);
    const selectedId = localStorage.getItem("mazu-run");
    setSelectedRunState(items.find((item) => item.id === selectedId) || items[0] || null);
  };
  useEffect(() => {
    Promise.all([api.health(), api.config(), api.scenarios()])
      .then(([healthData, configData, scenarioData]) => {
        setHealth(healthData); setConfig(configData); setScenarios(scenarioData);
      })
      .catch(() => setHealth(null));
    refreshRuns().catch(() => setRuns([]));
  }, []);
  const setLocale = (value: Locale) => { localStorage.setItem("mazu-locale", value); setLocaleState(value); };
  const setSelectedRun = (run: Run | null) => {
    if (run) localStorage.setItem("mazu-run", run.id);
    else localStorage.removeItem("mazu-run");
    setSelectedRunState(run);
  };
  const value = useMemo(
    () => ({ locale, setLocale, health, config, scenarios, runs, selectedRun, setSelectedRun, refreshRuns }),
    [locale, health, config, scenarios, runs, selectedRun],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

const nav = [
  ["/console", "01", "console"],
  ["/analysis", "02", "analysis"],
  ["/evidence", "03", "evidence"],
  ["/assistant", "04", "assistant"],
  ["/reports", "05", "reports"],
] as const;

const auxNav = [
  ["/overview", "↗", "overviewNav"],
  ["/knowledge-graph", "◇", "kgNav"],
] as const;

function Layout({ children }: { children: ReactNode }) {
  const { locale, setLocale, health, selectedRun } = useApp();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" to="/console">
          <span className="brand-mark"><i /></span>
          <span><strong>MAZU</strong><small>SAUDI / مَازُو</small></span>
        </Link>
        <nav>
          {nav.map(([path, number, key]) => (
            <NavLink key={path} to={path}><span>{number}</span>{t(locale, key)}</NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          {auxNav.map(([path, glyph, key]) => (
            <Link key={path} to={path}><span>{glyph}</span>{t(locale, key)}</Link>
          ))}
          <div className={`service-state ${health?.ready_for_inference ? "ready" : "degraded"}`}>
            <i />{health?.ready_for_inference ? t(locale, "localDataReady") : t(locale, "archiveModeShort")}
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="boundary-badge">
            <span>{t(locale, "historical")}</span>
            <small>{t(locale, "boundary")}</small>
          </div>
          {selectedRun && <Link className="active-run-chip" to="/analysis"><i /><span><small>{t(locale, "currentExercise")}</small><strong>{cityLabel(locale, selectedRun.city)} · {hazardLabel(locale, selectedRun.hazard)}</strong></span><b>{selectedRun.target_date.slice(5)}</b></Link>}
          <div className="top-actions">
            <span className="year-chip">{t(locale, "datasetYear")}</span>
            <div className="language-switch" aria-label="Language">
              <button className={locale === "zh" ? "active" : ""} onClick={() => setLocale("zh")}>中</button>
              <button className={locale === "en" ? "active" : ""} onClick={() => setLocale("en")}>EN</button>
            </div>
          </div>
        </header>
        {health && !health.ready_for_inference && (
          <div className="archive-banner"><strong>{t(locale, "archiveMode")}</strong><span>{t(locale, "archiveMessage")}</span></div>
        )}
        <main>{children}</main>
      </div>
    </div>
  );
}

function PageHeading({ eyebrow, title, lead, truth, archiveSensitive = true }: { eyebrow: string; title: string; lead: string; truth: string; archiveSensitive?: boolean }) {
  const { locale, health } = useApp();
  return <header className="page-heading">
    <span>{eyebrow}</span><h1>{title}</h1><p>{lead}</p>
    <div className="truth-strip" aria-label={locale === "zh" ? "真实性边界" : "Evidence boundary"}>
      <span>{!archiveSensitive || health?.ready_for_inference ? truth : (locale === "zh" ? "归档回放" : "Archive replay")}</span>
      <span>{locale === "zh" ? "2025历史数据 · 代理标签" : "2025 historical data · proxy labels"}</span>
    </div>
  </header>;
}

function ConsolePage() {
  const { locale, health, config, scenarios, runs, selectedRun, setSelectedRun, refreshRuns } = useApp();
  const navigate = useNavigate();
  const [city, setCity] = useState("Mecca");
  const [targetDate, setTargetDate] = useState("2025-08-04");
  const [hazard, setHazard] = useState("heatwave");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const applyScenario = (scenario: Scenario) => {
    setCity(scenario.city); setTargetDate(scenario.target_date); setHazard(scenario.hazard);
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const run = await api.createRun({ city, target_date: targetDate, hazard, locale });
      setSelectedRun(run); await refreshRuns();
    } catch { setError(t(locale, "runFailed")); }
    finally { setBusy(false); }
  };
  return (
    <>
      <PageHeading eyebrow={t(locale, "consoleEyebrow")} title={t(locale, "selectTask")} lead={t(locale, "selectTaskLead")} truth={locale === "zh" ? "本地模型按次重算" : "Local model recomputation"} />
      <section className="console-grid">
        <div className="console-controls panel">
          <div className="panel-label"><span>A / {t(locale, "taskControl")}</span><b>T−1 → T</b></div>
          <form onSubmit={submit}>
            <label>{t(locale, "city")}<select value={city} onChange={(e) => setCity(e.target.value)}>{config?.cities.map((item) => <option key={item} value={item}>{cityLabel(locale, item)}</option>)}</select></label>
            <label>{t(locale, "targetDate")}<input type="date" min="2025-01-02" max="2025-12-31" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} /></label>
            <label>{t(locale, "hazard")}<select value={hazard} onChange={(e) => setHazard(e.target.value)}>{config?.hazards.map((item) => <option key={item} value={item}>{hazardLabel(locale, item)}</option>)}</select></label>
            <div className="causal-note"><span>T−1</span><p>{locale === "zh" ? "系统仅读取目标日前一天可获得的指标，不使用目标日观测。" : "Only indicators available one day before the target are read."}</p></div>
            <button className="primary-button" disabled={busy || !health?.ready_for_inference}>{busy ? t(locale, "running") : t(locale, "run")}<span>→</span></button>
            {error && <p className="error-message">{error}</p>}
          </form>
        </div>
        <div className="scenario-column">
          <div className="section-title"><span>{t(locale, "scenarios")}</span><small>{t(locale, "curatedAudited")}</small></div>
          <div className="scenario-grid">
            {scenarios.map((scenario, index) => (
              <button key={scenario.id} className={`scenario-card ${scenario.kind}`} onClick={() => applyScenario(scenario)}>
                <span>0{index + 1}</span><strong>{locale === "zh" ? scenario.title_zh : scenario.title_en}</strong>
                <small>{cityLabel(locale, scenario.city)} · {scenario.target_date}</small>
              </button>
            ))}
          </div>
          <div className="history-panel panel">
            <div className="panel-label"><span>{t(locale, "recent")}</span><b>{runs.length.toString().padStart(2, "0")}</b></div>
            <div className="history-list">
              {runs.slice(0, 4).map((run) => <button key={run.id} className={run.id === selectedRun?.id ? "active" : ""} onClick={() => setSelectedRun(run)}><i /><span><strong>{cityLabel(locale, run.city)} · {hazardLabel(locale, run.hazard)}</strong><small>{run.target_date}</small></span><b>↗</b></button>)}
              {!runs.length && <p className="empty-inline">{t(locale, "noLocalRuns")}</p>}
            </div>
          </div>
        </div>
        <RiskBrief run={selectedRun} onOpen={() => navigate("/analysis")} locale={locale} />
      </section>
    </>
  );
}

function RiskBrief({ run, onOpen, locale }: { run: Run | null; onOpen: () => void; locale: Locale }) {
  if (!run?.result) return <aside className="risk-brief panel empty-brief"><div className="empty-radar"><i /><i /><i /><span>+</span></div><h2>{t(locale, "riskBrief")}</h2><p>{t(locale, "noRun")}</p></aside>;
  const { forecast, decision } = run.result;
  const rule = forecast.reflexive_check;
  const pct = Math.round(forecast.probability * 100);
  return (
    <aside className="risk-brief panel">
      <div className="panel-label"><span>B / {t(locale, "riskBrief")}</span><b className={`risk-level ${decision.alert_candidate ? "elevated" : ""}`}>{riskLevelLabel(locale, decision.level)}</b></div>
      <div className="brief-location"><div><span>{cityLabel(locale, forecast.city)}</span><h2>{hazardLabel(locale, forecast.hazard)}</h2></div><div className="coordinate">{forecast.grid_cell.lat}°N<br />{forecast.grid_cell.lon}°E</div></div>
      <div className="probability-dial" style={{ "--risk": `${pct * 3.6}deg` } as React.CSSProperties}><div><strong>{pct}</strong><span>%</span><small>{t(locale, "probability")}</small></div></div>
      <div className="brief-metrics">
        <div><span>{t(locale, "ruleScore")}</span><strong>{rule?.detection_engine_risk_score?.toFixed(2) ?? "—"}</strong></div>
        <div><span>{t(locale, "modelSpread")}</span><strong>±{forecast.uncertainty.std.toFixed(3)}</strong></div>
        <div><span>{t(locale, "inputDate")}</span><strong>{forecast.features_from_date.slice(5)}</strong></div>
        <div><span>ROC-AUC</span><strong>{forecast.model_verified_roc_auc.toFixed(3)}</strong></div>
      </div>
      <div className={`consistency ${rule?.consistency.includes("consistent") ? "agree" : "review"}`}><i /><div><span>{t(locale, "consistency")}</span><strong>{consistencyLabel(locale, rule?.consistency)}</strong></div></div>
      <button className="secondary-button" onClick={onOpen}>{t(locale, "openAnalysis")}<span>→</span></button>
    </aside>
  );
}

function EmptyRun() {
  const { locale } = useApp();
  return <div className="empty-page panel"><span>{t(locale, "noActiveExercise")}</span><h2>{t(locale, "noSelectedRun")}</h2><Link className="primary-button" to="/console">{t(locale, "console")} →</Link></div>;
}

function RiskMap({ run }: { run: Run }) {
  const { locale } = useApp();
  const canvas = useRef<HTMLCanvasElement>(null);
  const [layer, setLayer] = useState<FieldLayer>("probability");
  const [field, setField] = useState<FieldData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { setField(null); setError(""); api.field(run.id, layer).then(setField).catch(() => setError(t(locale, "fieldFailed"))); }, [run.id, layer, locale]);
  useEffect(() => {
    if (!field || !canvas.current) return;
    const element = canvas.current;
    const context = element.getContext("2d"); if (!context) return;
    const rect = element.getBoundingClientRect(); const ratio = window.devicePixelRatio || 1;
    element.width = rect.width * ratio; element.height = rect.height * ratio; context.scale(ratio, ratio);
    const cellWidth = rect.width / field.columns, cellHeight = rect.height / field.rows;
    context.fillStyle = "#edf4f2"; context.fillRect(0, 0, rect.width, rect.height);
    field.values.forEach((value, index) => {
      const normalized = layer === "uncertainty" ? Math.min(1, value / Math.max(field.maximum, 0.01)) : value;
      const hue = layer === "uncertainty" ? 205 + normalized * 105 : 166 - normalized * 142;
      context.fillStyle = `hsla(${hue}, ${48 + normalized * 30}%, ${92 - normalized * 40}%, .96)`;
      context.fillRect((index % field.columns) * cellWidth, Math.floor(index / field.columns) * cellHeight, cellWidth + .6, cellHeight + .6);
    });
  }, [field, layer]);
  return (
    <article className="map-panel panel">
      <div className="panel-label"><span>A / {t(locale, "saudiGridField")}</span><b>{field ? `${field.rows} × ${field.columns}` : t(locale, "loading")}</b></div>
      <div className="layer-switch">
        {(["probability", "rule_risk", "uncertainty"] as FieldLayer[]).map((item) => <button key={item} className={layer === item ? "active" : ""} onClick={() => setLayer(item)}>{item === "probability" ? t(locale, "layerProbability") : item === "rule_risk" ? t(locale, "layerRule") : t(locale, "layerUncertainty")}</button>)}
      </div>
      <div className="map-stage"><canvas ref={canvas} /><div className="grid-lines" /><span className="north">32°N</span><span className="south">16°N</span><span className="west">34°E</span><span className="east">56°E</span>{!field && !error && <div className="map-loading">{t(locale, "readingField")}</div>}{error && <div className="map-loading error-message">{error}</div>}</div>
      <div className="map-legend"><span>{field?.minimum.toFixed(2) ?? "0.00"}</span><i /><span>{field?.maximum.toFixed(2) ?? "1.00"}</span><small>{field?.cache === "hit" ? t(locale, "localCache") : t(locale, "modelDerived")}</small></div>
    </article>
  );
}

function AnalysisPage() {
  const { locale, selectedRun } = useApp();
  if (!selectedRun?.result) return <EmptyRun />;
  const { forecast, conditions } = selectedRun.result;
  const metrics = forecast.meteorological_metrics;
  const indicators = conditions.indicators || conditions.conditions || {};
  return (
    <>
      <PageHeading eyebrow={t(locale, "analysisEyebrow")} title={t(locale, "analysisTitle")} lead={t(locale, "analysisLead")} truth={locale === "zh" ? "模型与规则派生分析" : "Model- and rule-derived analysis"} />
      <section className="analysis-summary" aria-label={locale === "zh" ? "事件摘要" : "Event summary"}>
        <div className="summary-identity"><span>{cityLabel(locale, forecast.city)} · {hazardLabel(locale, forecast.hazard)}</span><strong>{forecast.target_date}</strong></div>
        <div><span>{locale === "zh" ? "模型概率" : "Model"}</span><strong>{Math.round(forecast.probability * 100)}%</strong></div>
        <div><span>{locale === "zh" ? "规则风险" : "Rule"}</span><strong>{forecast.reflexive_check?.detection_engine_risk_score.toFixed(2) ?? "—"}</strong></div>
        <div><span>{locale === "zh" ? "集合分歧" : "Spread"}</span><strong>±{forecast.uncertainty.std.toFixed(3)}</strong></div>
        <div className={forecast.reflexive_check?.consistency.includes("consistent") ? "summary-status agree" : "summary-status review"}><span>{locale === "zh" ? "复核状态" : "Cross-check"}</span><strong>{consistencyLabel(locale, forecast.reflexive_check?.consistency)}</strong></div>
      </section>
      <section className="analysis-grid">
        <RiskMap run={selectedRun} />
        <article className="metrics-panel panel">
          <div className="panel-label"><span>B / {t(locale, "reliability")}</span><b>{t(locale, "fixedThreshold")}</b></div>
          <div className="metric-hero"><span>{cityLabel(locale, forecast.city)} / {hazardLabel(locale, forecast.hazard)}</span><strong>{Math.round(forecast.probability * 100)}<small>%</small></strong><p>{forecast.target_date}</p></div>
          <div className="score-grid">{["pod", "far", "csi", "hss"].map((key) => <div key={key}><span>{key.toUpperCase()}</span><strong>{metrics[key] == null ? "—" : Number(metrics[key]).toFixed(3)}</strong></div>)}</div>
          <div className="boundary-card"><span>{t(locale, "interpretationBoundary")}</span><p>{locale === "zh" ? "代理标签上的单年时间外推结果，不等同于独立灾害真值或业务可靠性。" : "Single-year temporal holdout over proxy labels; not independent disaster truth or operational reliability."}</p></div>
        </article>
        <article className="indicator-panel panel">
          <div className="panel-label"><span>C / {t(locale, "inputIndicators")}</span><b>{forecast.features_from_date}</b></div>
          <div className="indicator-table">{Object.entries(indicators).slice(0, 12).map(([name, value]) => <div key={name}><span title={name}>{indicatorLabel(locale, name)}</span><strong>{value == null ? "NA" : Number(value).toFixed(2)}</strong></div>)}</div>
        </article>
        <article className="audit-panel panel">
          <div className="panel-label"><span>D / {t(locale, "crossCheck")}</span><b>{consistencyLabel(locale, forecast.reflexive_check?.consistency)}</b></div>
          <div className="comparison-bars"><div><span>{t(locale, "model")}</span><i style={{ width: `${forecast.probability * 100}%` }} /><strong>{forecast.probability.toFixed(2)}</strong></div><div><span>{t(locale, "rule")}</span><i style={{ width: `${(forecast.reflexive_check?.detection_engine_risk_score || 0) * 100}%` }} /><strong>{forecast.reflexive_check?.detection_engine_risk_score.toFixed(2)}</strong></div></div>
          <p>{ruleNote(locale, forecast.reflexive_check?.consistency)}</p>
          <div className="fired-list">{forecast.reflexive_check?.detection_engine_conditions_fired.map((item) => <span key={item} title={item}>{indicatorLabel(locale, item)}</span>)}</div>
        </article>
      </section>
    </>
  );
}

function EvidencePage() {
  const { locale, selectedRun } = useApp();
  const [selectedNode, setSelectedNode] = useState("hazard");
  if (!selectedRun?.result) return <EmptyRun />;
  const evidence = selectedRun.result.evidence;
  const indicators = evidence.contributing_indicators.slice(0, 6);
  const mechanisms = evidence.mechanisms.slice(0, 5);
  const citations = mechanisms.flatMap((item, mechanismIndex) =>
    item.citations.slice(0, 1).map((citation, index) => ({
      ...citation,
      id: `citation-${mechanismIndex}-${index}`,
      mechanismIndex,
      mechanism: item.mechanism,
    })),
  ).slice(0, 5);
  const indicatorY = (index: number) => indicators.length === 1 ? 280 : 80 + index * (400 / Math.max(1, indicators.length - 1));
  const mechanismY = (index: number) => mechanisms.length === 1 ? 280 : 85 + index * (390 / Math.max(1, mechanisms.length - 1));
  const citationY = (index: number) => citations.length === 1 ? 280 : 85 + index * (390 / Math.max(1, citations.length - 1));
  const selected =
    selectedNode === "hazard"
      ? {
          type: locale === "zh" ? "目标灾种" : "Target hazard",
          title: hazardLabel(locale, evidence.hazard),
          description: locale === "zh" ? "当前演练要解释的风险结果。所有连线都是解释和来源关系，不是自动发现的因果边。" : "The risk result being explained. Edges show explanation and provenance, not automatically discovered causality.",
          status: evidenceStatusLabel(locale, "RUN RESULT"),
        }
      : indicators.map((name) => ({
          id: `indicator-${name}`,
          type: locale === "zh" ? "观测指标" : "Observed indicator",
          title: indicatorLabel(locale, name),
          description: locale === "zh" ? `来自 ${selectedRun.result?.forecast.features_from_date} 的真实输入指标，作为本次演练的观测依据。` : `A real model input observed on ${selectedRun.result?.forecast.features_from_date}.`,
          status: evidenceStatusLabel(locale, "OBSERVED"),
        })).find((item) => item.id === selectedNode)
        || mechanisms.map((item) => ({
          id: `mechanism-${item.mechanism}`,
          type: locale === "zh" ? "机制断言" : "Mechanism assertion",
          title: mechanismLabel(locale, item.mechanism),
          description: mechanismDescription(locale, item.mechanism, item.description),
          status: evidenceStatusLabel(locale, item.literature_grounded ? "GROUNDED" : "REVIEW"),
        })).find((item) => item.id === selectedNode)
        || citations.map((item) => ({
          id: item.id,
          type: locale === "zh" ? "文献记录" : "Literature record",
          title: item.citation || (locale === "zh" ? "引文记录" : "Citation record"),
          description: locale === "zh"
            ? "该文献记录支持相应机制的有限范围说明，具体适用性仍需人工核对原始论文。"
            : item.verification_scope || item.review_status || "Applicability still requires human review.",
          status: evidenceStatusLabel(locale, item.review_status || "SCOPE LIMITED"),
        })).find((item) => item.id === selectedNode);
  return (
    <>
      <PageHeading eyebrow={t(locale, "evidenceEyebrow")} title={t(locale, "evidenceTitle")} lead={locale === "zh" ? "沿着关系线检查本次演练用了哪些观测、机制断言和文献记录；点击任一节点查看来源与核验状态。" : "Trace the observations, mechanism assertions and literature records used for this exercise. Select any node to audit its source and status."} truth={locale === "zh" ? "人工维护证据网络" : "Human-curated evidence network"} />
      <section className="evidence-workspace">
        <article className="network-panel">
          <div className="network-toolbar">
            <div><span>{t(locale, "eventSubgraph")}</span><strong>{indicators.length + mechanisms.length + citations.length + 1} {t(locale, "nodes")} · {indicators.length + mechanisms.length + citations.length} {t(locale, "edges")}</strong></div>
            <div className="network-legend"><span><i className="observation" />{locale === "zh" ? "观测" : "Observation"}</span><span><i className="assertion" />{locale === "zh" ? "机制" : "Mechanism"}</span><span><i className="hazard" />{locale === "zh" ? "灾种" : "Hazard"}</span><span><i className="citation" />{locale === "zh" ? "文献" : "Citation"}</span></div>
          </div>
          <div className="network-scroll">
            <div className="network-canvas">
              <svg viewBox="0 0 1000 560" aria-hidden="true">
                <defs><marker id="graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" /></marker></defs>
                {indicators.map((item, index) => <path key={`indicator-edge-${item}`} className="edge observation-edge" d={`M 150 ${indicatorY(index)} C 330 ${indicatorY(index)}, 500 280, 665 280`} />)}
                {mechanisms.map((item, index) => <path key={`mechanism-edge-${item.mechanism}`} className="edge mechanism-edge" d={`M 465 ${mechanismY(index)} C 555 ${mechanismY(index)}, 560 280, 665 280`} />)}
                {citations.map((item, index) => <path key={`citation-edge-${item.id}`} className="edge citation-edge" d={`M 855 ${citationY(index)} C 725 ${citationY(index)}, 600 ${mechanismY(item.mechanismIndex)}, 465 ${mechanismY(item.mechanismIndex)}`} />)}
                <text className="edge-label" x="255" y="265">{locale === "zh" ? "本次观测" : "observed for run"}</text>
                <text className="edge-label" x="520" y="265">{locale === "zh" ? "解释断言" : "explains"}</text>
                <text className="edge-label" x="745" y="265">{locale === "zh" ? "文献支持" : "grounded by"}</text>
              </svg>
              {indicators.map((item, index) => <button key={item} className={`network-node observation ${selectedNode === `indicator-${item}` ? "selected" : ""}`} style={{ left: "12%", top: `${indicatorY(index) / 5.6}%` }} onClick={() => setSelectedNode(`indicator-${item}`)} title={item}><small>{t(locale, "indicatorNode")}</small><strong>{indicatorLabel(locale, item)}</strong></button>)}
              {mechanisms.map((item, index) => <button key={item.mechanism} className={`network-node assertion ${selectedNode === `mechanism-${item.mechanism}` ? "selected" : ""}`} style={{ left: "42%", top: `${mechanismY(index) / 5.6}%` }} onClick={() => setSelectedNode(`mechanism-${item.mechanism}`)} title={item.mechanism}><small>{t(locale, "mechanismNode")}</small><strong>{mechanismLabel(locale, item.mechanism)}</strong></button>)}
              <button className={`network-node hazard ${selectedNode === "hazard" ? "selected" : ""}`} style={{ left: "70%", top: "50%" }} onClick={() => setSelectedNode("hazard")}><small>{t(locale, "hazardNode")}</small><strong>{hazardLabel(locale, evidence.hazard)}</strong><b>{Math.round(selectedRun.result.forecast.probability * 100)}%</b></button>
              {citations.map((item, index) => <button key={item.id} className={`network-node citation ${selectedNode === item.id ? "selected" : ""}`} style={{ left: "89%", top: `${citationY(index) / 5.6}%` }} onClick={() => setSelectedNode(item.id)}><small>{t(locale, "citationNode")}</small><strong>{locale === "zh" ? "文献记录" : "Literature"}</strong></button>)}
              <div className="network-selection-card" aria-live="polite"><span>{selected?.type}</span><strong>{selected?.title}</strong><small>{selected?.status}</small></div>
            </div>
          </div>
          <div className="network-boundary"><strong>{locale === "zh" ? "关系边界" : "Edge boundary"}</strong><span>{evidenceBoundary(locale, evidence.claim_boundary)}</span></div>
        </article>
        <aside className="node-inspector">
          <div className="inspector-heading"><span>{t(locale, "nodeInspector")}</span><b>{selected?.status}</b></div>
          <div className="inspector-content"><small>{selected?.type}</small><h2>{selected?.title}</h2><p>{selected?.description}</p></div>
          <div className="relation-register">
            <span>{t(locale, "relationsInView")}</span>
            <div><i className="observation" /><p><strong>{locale === "zh" ? "观测支持" : "Observed for run"}</strong><small>{indicators.length} {locale === "zh" ? "个前一日输入" : "previous-day inputs"}</small></p></div>
            <div><i className="assertion" /><p><strong>{locale === "zh" ? "机制解释" : "Mechanism explains"}</strong><small>{mechanisms.length} {locale === "zh" ? "条人工断言" : "human assertions"}</small></p></div>
            <div><i className="citation" /><p><strong>{locale === "zh" ? "文献支撑" : "Grounded by"}</strong><small>{citations.length} {locale === "zh" ? "条有限范围记录" : "scoped records"}</small></p></div>
          </div>
        </aside>
      </section>
    </>
  );
}

function AssistantPage() {
  const { locale, selectedRun, health } = useApp();
  const [tab, setTab] = useState<"live" | "examples">("live");
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState<{ content: string; mode: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (!message.trim() || !selectedRun) return; setBusy(true);
    try {
      const response = await api.message(selectedRun.id, message, locale);
      setAnswer({ content: response.content, mode: response.mode });
    } finally { setBusy(false); }
  };
  const tabs = (
    <div className="example-tabs">
      <button className={tab === "live" ? "active" : ""} onClick={() => setTab("live")}>{t(locale, "liveAssistantTab")}</button>
      <button className={tab === "examples" ? "active" : ""} onClick={() => setTab("examples")}>{t(locale, "historicalExamplesTab")}</button>
    </div>
  );
  if (tab === "examples") {
    return (
      <>
        <PageHeading eyebrow={t(locale, "assistantEyebrow")} title={t(locale, "assistantTitle")} lead={locale === "zh" ? "它不是另一个聊天页面：系统把当前演练自动整理成结论、依据、分歧、限制和下一步，方便评委快速理解一次运行。" : "This is not another chat screen. It turns the current run into a conclusion, evidence, disagreement, limitations and next steps."} truth={health?.llm_available ? (locale === "zh" ? "自动简报 + 可选 AI 追问" : "Automatic brief + optional AI") : (locale === "zh" ? "确定性自动简报" : "Deterministic automatic brief")} />
        {tabs}
        <HistoricalExamplesPanel />
      </>
    );
  }
  if (!selectedRun?.result) return <><PageHeading eyebrow={t(locale, "assistantEyebrow")} title={t(locale, "assistantTitle")} lead={locale === "zh" ? "它不是另一个聊天页面：系统把当前演练自动整理成结论、依据、分歧、限制和下一步，方便评委快速理解一次运行。" : "This is not another chat screen. It turns the current run into a conclusion, evidence, disagreement, limitations and next steps."} truth={health?.llm_available ? (locale === "zh" ? "自动简报 + 可选 AI 追问" : "Automatic brief + optional AI") : (locale === "zh" ? "确定性自动简报" : "Deterministic automatic brief")} />{tabs}<EmptyRun /></>;
  const forecast = selectedRun.result.forecast;
  const decision = selectedRun.result.decision;
  const rule = forecast.reflexive_check;
  const conditionValues = selectedRun.result.conditions.indicators || selectedRun.result.conditions.conditions || {};
  const evidenceIndicators = selectedRun.result.evidence.contributing_indicators;
  const topIndicators = evidenceIndicators
    .map((name) => [name, conditionValues[name]] as const)
    .filter(([, value]) => value != null)
    .slice(0, 4);
  return (
    <>
      <PageHeading eyebrow={t(locale, "assistantEyebrow")} title={t(locale, "assistantTitle")} lead={locale === "zh" ? "它不是另一个聊天页面：系统把当前演练自动整理成结论、依据、分歧、限制和下一步，方便评委快速理解一次运行。" : "This is not another chat screen. It turns the current run into a conclusion, evidence, disagreement, limitations and next steps."} truth={health?.llm_available ? (locale === "zh" ? "自动简报 + 可选 AI 追问" : "Automatic brief + optional AI") : (locale === "zh" ? "确定性自动简报" : "Deterministic automatic brief")} />
      {tabs}
      <section className="brief-workflow">
        <div><span>01</span><p><strong>{locale === "zh" ? "读取运行记录" : "Read run record"}</strong><small>{locale === "zh" ? "概率、指标、阈值" : "Probability, inputs, threshold"}</small></p></div>
        <i>→</i>
        <div><span>02</span><p><strong>{locale === "zh" ? "交叉复核" : "Cross-check"}</strong><small>{locale === "zh" ? "模型、规则、证据" : "Model, rules, evidence"}</small></p></div>
        <i>→</i>
        <div><span>03</span><p><strong>{locale === "zh" ? "形成决策简报" : "Produce brief"}</strong><small>{locale === "zh" ? "结论、限制、下一步" : "Finding, limits, next step"}</small></p></div>
      </section>
      <section className="decision-layout">
        <article className="decision-hero">
          <div className="decision-kicker"><span>{t(locale, "historicalExerciseLabel")}</span><b>{riskLevelLabel(locale, decision.level)}</b></div>
          <div className="decision-place"><small>{selectedRun.target_date}</small><h2>{cityLabel(locale, selectedRun.city)} · {hazardLabel(locale, selectedRun.hazard)}</h2></div>
          <div className="decision-probability"><strong>{Math.round(forecast.probability * 100)}</strong><span>%</span><p>{locale === "zh" ? "模型风险概率" : "model risk probability"}</p></div>
          <div className="decision-statement">
            <span>{locale === "zh" ? "一句话结论" : "Bottom line"}</span>
            <p>{locale === "zh" ? `模型超过固定阈值 ${Math.round(decision.threshold * 100)}%，本次历史演练进入“${riskLevelLabel(locale, decision.level)}”等级；仍需结合规则分歧和代理标签边界人工复核。` : `The model exceeds the fixed ${Math.round(decision.threshold * 100)}% threshold and enters the ${riskLevelLabel(locale, decision.level)} tier; rule disagreement and proxy-label limits still require review.`}</p>
          </div>
        </article>
        <div className="brief-cards">
          <article><span>A / {locale === "zh" ? "主要依据" : "DRIVERS"}</span><h3>{locale === "zh" ? "前一日输入指标" : "Previous-day indicators"}</h3><div className="driver-list">{topIndicators.map(([name, value]) => <div key={name}><small title={name}>{indicatorLabel(locale, name)}</small><strong>{Number(value).toFixed(2)}</strong></div>)}</div><Link to="/analysis">{locale === "zh" ? "查看完整分析" : "Open full analysis"} →</Link></article>
          <article><span>B / {t(locale, "crossCheck")}</span><h3>{locale === "zh" ? "模型与规则是否一致？" : "Do model and rules agree?"}</h3><div className="crosscheck-score"><div><small>{t(locale, "model")}</small><strong>{forecast.probability.toFixed(2)}</strong></div><i>↔</i><div><small>{t(locale, "rule")}</small><strong>{rule?.detection_engine_risk_score.toFixed(2) ?? "—"}</strong></div></div><p>{consistencyLabel(locale, rule?.consistency)}</p><Link to="/evidence">{locale === "zh" ? "沿证据网络核验" : "Audit the evidence network"} →</Link></article>
          <article className="limits-card"><span>C / {locale === "zh" ? "必须说明的限制" : "LIMITS"}</span><h3>{locale === "zh" ? "这个结果能说明什么？" : "What does this result mean?"}</h3><ul><li>{locale === "zh" ? "2025单年历史数据" : "2025 single-year historical data"}</li><li>{locale === "zh" ? "代理标签，不是独立灾情真值" : "Proxy labels, not independent disaster truth"}</li><li>{locale === "zh" ? "历史演练，不是业务预警" : "Historical exercise, not an operational warning"}</li></ul><Link to="/reports">{locale === "zh" ? "生成带边界的报告" : "Generate a bounded report"} →</Link></article>
        </div>
      </section>
      <section className="followup-panel">
        <div className="followup-heading"><div><span>{t(locale, "optionalFollowup")}</span><h2>{locale === "zh" ? "对这份简报继续追问" : "Ask a follow-up about this brief"}</h2></div><b>{health?.llm_available ? t(locale, "deepseekAvailable") : t(locale, "deterministicTemplate")}</b></div>
        {answer && <div className="followup-answer"><span>{answer.mode === "deepseek" ? (locale === "zh" ? "DeepSeek / 有边界 JSON" : "DeepSeek / bounded JSON") : (locale === "zh" ? "MAZU / 确定性摘要" : "MAZU / deterministic summary")}</span><p>{answer.content}</p></div>}
        <form onSubmit={submit}><textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder={locale === "zh" ? "例如：为什么模型和规则不一致？" : "For example: Why do model and rules disagree?"} /><button className="primary-button" disabled={busy}>{busy ? "…" : t(locale, "send")}<span>↗</span></button></form>
        <p className="followup-boundary">{locale === "zh" ? "追问只读取当前运行记录，不能修改概率、等级或 CAP。" : "Follow-up only reads the current run; it cannot modify probability, level or CAP."}</p>
      </section>
    </>
  );
}

interface AgentExampleToolCall { call: string; output: Record<string, unknown> | null }
interface AgentExample { id: string; question: string; toolCalls: AgentExampleToolCall[]; answerHtml: string }

function HistoricalExamplesPanel() {
  const { locale } = useApp();
  const examples = agentExamples as AgentExample[];
  return (
    <section className="example-list">
      {examples.map((example) => (
        <article key={example.id} className="example-card panel">
          <div className="panel-label"><span>{t(locale, "exampleQuestionLabel")}</span></div>
          <p className="example-question">{example.question}</p>
          <div className="example-toolcalls">
            <span className="example-subhead">{t(locale, "exampleToolCallLabel")}</span>
            {example.toolCalls.map((tool, index) => (
              <details key={`${example.id}-${index}`} className="example-toolcall">
                <summary>{tool.call}</summary>
                <pre>{JSON.stringify(tool.output, null, 2)}</pre>
              </details>
            ))}
          </div>
          <div className="example-answer">
            <span className="example-subhead">{t(locale, "exampleAnswerLabel")}</span>
            <div dangerouslySetInnerHTML={{ __html: example.answerHtml }} />
          </div>
        </article>
      ))}
    </section>
  );
}

function ReportsPage() {
  const { locale, selectedRun } = useApp();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [generated, setGenerated] = useState<{ report?: string; evidence?: string; cap?: string; note?: string }>({});
  useEffect(() => { api.reports().then(setReports).catch(() => setReports([])); }, []);
  const visibleReports = reports.filter((report) => report.language === locale);
  const createReport = async () => {
    if (!selectedRun) return; const result = await api.createReport(selectedRun.id);
    setGenerated((value) => ({ ...value, report: `/api/v1/artifacts/${result.report.id}`, evidence: `/api/v1/artifacts/${result.evidence.id}` }));
  };
  const createCap = async () => {
    if (!selectedRun) return; const result = await api.cap(selectedRun.id);
    const artifact = result.artifact as { id?: string } | undefined;
    setGenerated((value) => ({
      ...value,
      cap: artifact?.id ? `/api/v1/artifacts/${artifact.id}` : undefined,
      note: result.reason
        ? (locale === "zh" ? "当前结果未达到既有阈值，因此不生成 CAP Exercise。" : String(result.reason))
        : "",
    }));
  };
  return (
    <>
      <PageHeading eyebrow={t(locale, "reportsEyebrow")} title={t(locale, "reportsTitle")} lead={locale === "zh" ? "固定研究材料与每次演练的可下载证据包统一归档。" : "Fixed research materials and run-specific evidence packages in one library."} truth={locale === "zh" ? "运行结果动态生成" : "Generated from run results"} />
      <section className="report-layout">
        <article className="submission-panel panel">
          <div className="panel-label"><span>A / {t(locale, "currentRunArtifacts")}</span><b>{selectedRun ? t(locale, "ready") : t(locale, "noRunShort")}</b></div>
          {selectedRun?.result ? <>
            <div className="submission-runline"><div><span>{selectedRun.target_date}</span><h2>{cityLabel(locale, selectedRun.city)} · {hazardLabel(locale, selectedRun.hazard)}</h2></div><p><strong>{Math.round(selectedRun.result.forecast.probability * 100)}%</strong><small>{riskLevelLabel(locale, selectedRun.result.decision.level)}</small></p></div>
            <div className="artifact-grid">
              <article><span>01</span><h3>{locale === "zh" ? "双语演练报告" : "Bilingual run report"}</h3><p>{locale === "zh" ? "适合打印或保存为PDF，包含结论、指标和边界。" : "Print-ready findings, indicators and boundaries."}</p><button onClick={createReport}>{generated.report ? (locale === "zh" ? "重新生成" : "Regenerate") : t(locale, "generateReport")}<b>→</b></button></article>
              <article><span>02</span><h3>{locale === "zh" ? "JSON证据包" : "JSON evidence pack"}</h3><p>{locale === "zh" ? "保存模型、规则、证据版本和完整审计字段。" : "Model, rule, evidence versions and audit fields."}</p>{generated.evidence ? <a href={generated.evidence}>{locale === "zh" ? "下载证据包" : "Download evidence"}<b>↓</b></a> : <small>{locale === "zh" ? "随报告一同生成" : "Generated with the report"}</small>}</article>
              <article><span>03</span><h3>CAP Exercise XML</h3><p>{locale === "zh" ? "仅达到既有阈值时生成，状态始终为Exercise。" : "Available only above the fixed threshold; always Exercise."}</p><button onClick={createCap}>{generated.cap ? (locale === "zh" ? "重新生成" : "Regenerate") : t(locale, "generateCap")}<b>→</b></button></article>
            </div>
            {(generated.report || generated.cap || generated.note) && <div className="artifact-downloads">{generated.report && <a href={generated.report} target="_blank">HTML / PDF ↓</a>}{generated.cap && <a href={generated.cap}>CAP XML ↓</a>}{generated.note && <p>{generated.note}</p>}</div>}
          </> : <p className="submission-empty">{t(locale, "noSelectedRun")}</p>}
        </article>
        <article className="library-panel panel">
          <div className="panel-label"><span>B / {t(locale, "documentLibrary")}</span><b>{visibleReports.length} {t(locale, "items")}</b></div>
          <div className="report-list">{visibleReports.map((report) => <a key={report.id} href={report.url} target="_blank" rel="noreferrer"><span>{locale === "zh" ? reportKindLabel(locale, report.kind).slice(0, 1) : report.kind.slice(0, 2).toUpperCase()}</span><div><strong>{report.title}</strong><small>{reportKindLabel(locale, report.kind)} · {report.language.toUpperCase()}</small></div><b>↗</b></a>)}</div>
        </article>
      </section>
    </>
  );
}

const overviewStats = [
  ["365", "overviewStatDays"],
  ["10 km", "overviewStatResolution"],
  ["22", "overviewStatIndicators"],
  ["60 / 145", "overviewStatEvidence"],
  ["6", "overviewStatCitations"],
  ["3", "overviewStatHazards"],
] as const;

const overviewSections = [
  { titleKey: "overviewSection01Title", leadKey: "overviewSection01Lead", image: "risk_annual_hotspots.png" },
  { titleKey: "overviewSection02Title", leadKey: "overviewSection02Lead", image: undefined },
  { titleKey: "overviewSection03Title", leadKey: "overviewSection03Lead", image: "forecast_vs_actual.png" },
  { titleKey: "overviewSection04Title", leadKey: "overviewSection04Lead", image: "map_junjul_dust.png" },
  { titleKey: "overviewSection05Title", leadKey: "overviewSection05Lead", image: "agent_view_preview.png" },
  { titleKey: "overviewSection06Title", leadKey: "overviewSection06Lead", image: "architecture_diagram.png" },
] as const;

function OverviewPage() {
  const { locale } = useApp();
  return (
    <>
      <PageHeading eyebrow={t(locale, "overviewEyebrow")} title={t(locale, "overviewTitle")} lead={t(locale, "overviewLead")} truth={locale === "zh" ? "历史数据 · 参考资料" : "Historical data · reference material"} />
      <section className="overview-hero panel">
        <div className="overview-stats">
          {overviewStats.map(([value, key]) => (
            <div key={key}><strong>{value}</strong><span>{t(locale, key)}</span></div>
          ))}
        </div>
      </section>
      {overviewSections.map((section) => (
        <section key={section.titleKey} className="overview-section panel">
          <div className="panel-label"><span>{t(locale, section.titleKey)}</span></div>
          <p>{t(locale, section.leadKey)}</p>
          {section.image && (
            <figure className="overview-figure">
              <img src={`/media/${section.image}`} alt={t(locale, section.titleKey)} loading="lazy" />
            </figure>
          )}
        </section>
      ))}
    </>
  );
}

interface KgPoint { id: string; x: number; y: number }

const kgTypeColor: Record<string, string> = {
  observation: "#78889b",
  indicator: "var(--cyan)",
  state: "var(--teal)",
  episode: "#8c6ed3",
  context: "var(--mint)",
  mechanism: "var(--navy)",
  assertion: "var(--amber)",
  provenance: "#6d7b58",
  forecast: "var(--red)",
};

function KnowledgeGraphPage() {
  const { locale } = useApp();
  const [data, setData] = useState<OntologyGraph | null>(null);
  const [search, setSearch] = useState("");
  const [module, setModule] = useState("");
  const [activeEdgeTypes, setActiveEdgeTypes] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<string | null>(null);
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const modules = ["observation", "indicator", "state", "episode", "context", "mechanism", "assertion", "provenance", "forecast"];
  const edgeTypes = useMemo(
    () => Array.from(new Set((data?.edges || []).map((edge) => edge.predicate_label))),
    [data],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError("");
      api.ontologyGraph(search, module)
        .then((payload) => {
          setData(payload);
          setSelected((current) => payload.nodes.some((node) => node.iri === current) ? current : null);
          setActiveEdgeTypes(new Set(payload.edges.map((edge) => edge.predicate_label)));
        })
        .catch(() => {
          setData(null);
          setError(t(locale, "kgLoadFailed"));
        })
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search, module, locale]);

  useEffect(() => {
    if (!data) {
      setPositions({});
      return;
    }
    const nodes = data.nodes.map((node) => ({ ...node, id: node.iri }));
    const links = data.edges.map((edge) => ({ ...edge }));
    const simulation = forceSimulation(nodes as never[])
      .force("charge", forceManyBody().strength(-105))
      .force("link", forceLink(links as never[]).id((node: unknown) => (node as { id: string }).id).distance(76).strength(0.28))
      .force("center", forceCenter(500, 300))
      .force("collide", forceCollide(25))
      .stop();
    for (let i = 0; i < 240; i += 1) simulation.tick();
    const next: Record<string, { x: number; y: number }> = {};
    (nodes as unknown as Array<{ id: string; x: number; y: number }>).forEach((node) => {
      next[node.id] = {
        x: Math.max(28, Math.min(972, node.x)),
        y: Math.max(28, Math.min(572, node.y)),
      };
    });
    setPositions(next);
  }, [data]);

  const tree = useMemo(() => {
    const points: KgPoint[] = Object.entries(positions).map(([id, p]) => ({ id, x: p.x, y: p.y }));
    return quadtree<KgPoint>().x((p) => p.x).y((p) => p.y).addAll(points);
  }, [positions]);

  const toggleEdgeType = (value: string) => setActiveEdgeTypes((prev) => {
    const next = new Set(prev); if (next.has(value)) next.delete(value); else next.add(value); return next;
  });

  const visibleNodes = data?.nodes || [];
  const visibleIds = new Set(visibleNodes.map((node) => node.iri));
  const visibleLinks = (data?.edges || []).filter((edge) =>
    activeEdgeTypes.has(edge.predicate_label)
    && visibleIds.has(edge.source)
    && visibleIds.has(edge.target)
  );
  const selectedNode = selected ? data?.nodes.find((node) => node.iri === selected) : null;
  const relatedLinks = selected
    ? (data?.edges || []).filter((edge) => edge.source === selected || edge.target === selected)
    : [];
  const nodeByIri = new Map((data?.nodes || []).map((node) => [node.iri, node]));
  const nodeLabel = (node: OntologyNode) =>
    (locale === "zh" ? node.label_zh : node.label_en) || node.label || node.local_name;
  const edgePeer = (edge: OntologyEdge) =>
    nodeByIri.get(edge.source === selected ? edge.target : edge.source);

  const handleCanvasClick = (event: MouseEvent<SVGSVGElement>) => {
    const svg = event.currentTarget;
    const rect = svg.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 1000;
    const y = ((event.clientY - rect.top) / rect.height) * 600;
    const found = tree.find(x, y, 40);
    if (found) setSelected(found.id);
  };

  return (
    <>
      <PageHeading eyebrow={t(locale, "kgEyebrow")} title={t(locale, "kgTitle")} lead={t(locale, "kgLead")} truth={t(locale, "kgLiveDatabase")} archiveSensitive={false} />
      <section className="kg-page">
        <article className="kg-canvas-panel panel">
          <div className="panel-label">
            <span>{data?.node_count ?? 0} {t(locale, "kgNodeCountLabel")} · {data?.edge_count ?? 0} {t(locale, "kgEdgeCountLabel")}</span>
            <b>{t(locale, "kgVersion")} {data?.ontology.version || "—"}</b>
          </div>
          <label className="kg-search-field">
            <span className="sr-only">{t(locale, "kgSearchPlaceholder")}</span>
            <input className="kg-search-bar" value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t(locale, "kgSearchPlaceholder")} />
            {search && <button type="button" onClick={() => setSearch("")} aria-label={locale === "zh" ? "清除搜索" : "Clear search"}>×</button>}
          </label>
          <div className="kg-filter-chips" aria-label={t(locale, "kgFilterByType")}>
            {["", ...modules].map((value) => (
              <button key={value || "all"} className={module === value ? "active" : ""} style={{ borderColor: value ? kgTypeColor[value] : "var(--line)" }} onClick={() => setModule(value)}>
                {value && <i style={{ background: kgTypeColor[value] }} />}{value || t(locale, "kgAllModules")}
              </button>
            ))}
          </div>
          {!!edgeTypes.length && <div className="kg-filter-chips kg-edge-filters" aria-label={t(locale, "kgFilterByEdge")}>
            {edgeTypes.map((type) => (
              <button key={type} className={activeEdgeTypes.has(type) ? "active" : ""} onClick={() => toggleEdgeType(type)}>{type}</button>
            ))}
          </div>}
          <div className="kg-canvas">
            {loading && <div className="kg-state-message"><i />{t(locale, "kgLoading")}</div>}
            {!loading && error && <div className="kg-state-message error-message">{error}</div>}
            {!loading && !error && !visibleNodes.length && <div className="kg-state-message">{t(locale, "kgEmpty")}</div>}
            {!loading && !error && !!visibleNodes.length && <svg viewBox="0 0 1000 600" onClick={handleCanvasClick} aria-label={t(locale, "kgTitle")}>
              {visibleLinks.map((link, index) => {
                const from = positions[link.source]; const to = positions[link.target];
                if (!from || !to) return null;
                return <line key={`${link.source}-${link.target}-${index}`} className={`kg-edge ${selected && (link.source === selected || link.target === selected) ? "related" : ""}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y}><title>{link.predicate_label}</title></line>;
              })}
              {visibleNodes.map((node) => {
                const point = positions[node.iri]; if (!point) return null;
                return (
                  <g key={node.iri} className={`kg-node ${selected === node.iri ? "selected" : ""}`} transform={`translate(${point.x}, ${point.y})`} tabIndex={0} role="button" aria-label={nodeLabel(node)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setSelected(node.iri); }} onClick={(event) => { event.stopPropagation(); setSelected(node.iri); }}>
                    <circle r={selected === node.iri ? 10 : 7} fill={kgTypeColor[node.module || ""] || "var(--muted)"} />
                    <title>{nodeLabel(node)}</title>
                  </g>
                );
              })}
            </svg>}
          </div>
        </article>
        <aside className="kg-node-inspector panel">
          <div className="panel-label"><span>{selectedNode?.module || t(locale, "kgFilterByType")}</span></div>
          {selectedNode ? (
            <>
              <h3>{nodeLabel(selectedNode)}</h3>
              <p className="kg-definition">{(locale === "zh" ? selectedNode.definition_zh : selectedNode.definition_en) || selectedNode.definition_zh || selectedNode.definition_en || "—"}</p>
              <dl>
                <div><dt>{t(locale, "kgModule")}</dt><dd>{selectedNode.module || "—"}</dd></div>
                <div><dt>{t(locale, "kgResourceType")}</dt><dd>{selectedNode.resource_type.split(/[/#:]/).pop()}</dd></div>
                <div><dt>IRI</dt><dd title={selectedNode.iri}>{selectedNode.local_name}</dd></div>
              </dl>
              <table className="kg-edge-table">
                <thead><tr><th>{t(locale, "kgEdgeCountLabel")}</th><th>predicate</th></tr></thead>
                <tbody>
                  {relatedLinks.map((link) => (
                    <tr key={link.id} onClick={() => { const peer = edgePeer(link); if (peer) setSelected(peer.iri); }} className={edgePeer(link) ? "clickable" : ""}>
                      <td>{edgePeer(link) ? nodeLabel(edgePeer(link)!) : (link.source === selectedNode.iri ? link.target : link.source).split(":").pop()}</td>
                      <td>{link.predicate_label}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : <p className="empty-inline">{t(locale, "kgSelectNode")}</p>}
        </aside>
      </section>
      <p className="kg-claim-boundary">{t(locale, "kgClaimBoundary")}</p>
    </>
  );
}

export default function App() {
  return <AppProvider><Layout><Routes><Route path="/" element={<Navigate to="/console" replace />} /><Route path="/console" element={<ConsolePage />} /><Route path="/analysis" element={<AnalysisPage />} /><Route path="/evidence" element={<EvidencePage />} /><Route path="/assistant" element={<AssistantPage />} /><Route path="/reports" element={<ReportsPage />} /><Route path="/overview" element={<OverviewPage />} /><Route path="/knowledge-graph" element={<KnowledgeGraphPage />} /><Route path="*" element={<Navigate to="/console" replace />} /></Routes></Layout></AppProvider>;
}
