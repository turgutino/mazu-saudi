import { createContext, useContext, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { api } from "./api";
import { cityLabel, hazardLabel, t } from "./i18n";
import type { Config, FieldData, FieldLayer, Health, Locale, ReportItem, Run, Scenario } from "./types";

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

function Layout({ children }: { children: ReactNode }) {
  const { locale, setLocale, health } = useApp();
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
          <a href="/legacy/index.html"><span>↗</span>{t(locale, "archive")}</a>
          <div className={`service-state ${health?.ready_for_inference ? "ready" : "degraded"}`}>
            <i />{health?.ready_for_inference ? "LOCAL DATA READY" : "ARCHIVE MODE"}
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="boundary-badge">
            <span>{t(locale, "historical")}</span>
            <small>{t(locale, "boundary")}</small>
          </div>
          <div className="top-actions">
            <span className="year-chip">DATASET / 2025</span>
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

function PageHeading({ eyebrow, title, lead, truth }: { eyebrow: string; title: string; lead: string; truth: string }) {
  const { locale, health } = useApp();
  return <header className="page-heading">
    <span>{eyebrow}</span><h1>{title}</h1><p>{lead}</p>
    <div className="truth-strip" aria-label={locale === "zh" ? "真实性边界" : "Evidence boundary"}>
      <span>{health?.ready_for_inference ? truth : (locale === "zh" ? "归档回放" : "Archive replay")}</span>
      <span>{locale === "zh" ? "2025历史数据" : "2025 historical data"}</span>
      <span>{locale === "zh" ? "代理标签验证" : "Proxy-label validation"}</span>
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
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to run exercise"); }
    finally { setBusy(false); }
  };
  return (
    <>
      <PageHeading eyebrow="WARNING WORKFLOW / 01" title={t(locale, "selectTask")} lead={t(locale, "selectTaskLead")} truth={locale === "zh" ? "本地模型按次重算" : "Local model recomputation"} />
      <section className="console-grid">
        <div className="console-controls panel">
          <div className="panel-label"><span>A / TASK CONTROL</span><b>T−1 → T</b></div>
          <form onSubmit={submit}>
            <label>{t(locale, "city")}<select value={city} onChange={(e) => setCity(e.target.value)}>{config?.cities.map((item) => <option key={item} value={item}>{cityLabel(locale, item)} / {item}</option>)}</select></label>
            <label>{t(locale, "targetDate")}<input type="date" min="2025-01-02" max="2025-12-31" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} /></label>
            <label>{t(locale, "hazard")}<select value={hazard} onChange={(e) => setHazard(e.target.value)}>{config?.hazards.map((item) => <option key={item} value={item}>{hazardLabel(locale, item)}</option>)}</select></label>
            <div className="causal-note"><span>T−1</span><p>{locale === "zh" ? "系统仅读取目标日前一天可获得的指标，不使用目标日观测。" : "Only indicators available one day before the target are read."}</p></div>
            <button className="primary-button" disabled={busy || !health?.ready_for_inference}>{busy ? t(locale, "running") : t(locale, "run")}<span>→</span></button>
            {error && <p className="error-message">{error}</p>}
          </form>
        </div>
        <div className="scenario-column">
          <div className="section-title"><span>{t(locale, "scenarios")}</span><small>CURATED / AUDITED</small></div>
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
              {!runs.length && <p className="empty-inline">{locale === "zh" ? "尚无本地演练记录" : "No local exercises yet"}</p>}
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
      <div className="panel-label"><span>B / {t(locale, "riskBrief").toUpperCase()}</span><b className={`risk-level ${decision.alert_candidate ? "elevated" : ""}`}>{decision.level}</b></div>
      <div className="brief-location"><div><span>{cityLabel(locale, forecast.city)}</span><h2>{hazardLabel(locale, forecast.hazard)}</h2></div><div className="coordinate">{forecast.grid_cell.lat}°N<br />{forecast.grid_cell.lon}°E</div></div>
      <div className="probability-dial" style={{ "--risk": `${pct * 3.6}deg` } as React.CSSProperties}><div><strong>{pct}</strong><span>%</span><small>{t(locale, "probability")}</small></div></div>
      <div className="brief-metrics">
        <div><span>{t(locale, "ruleScore")}</span><strong>{rule?.detection_engine_risk_score?.toFixed(2) ?? "—"}</strong></div>
        <div><span>{t(locale, "modelSpread")}</span><strong>±{forecast.uncertainty.std.toFixed(3)}</strong></div>
        <div><span>{t(locale, "inputDate")}</span><strong>{forecast.features_from_date.slice(5)}</strong></div>
        <div><span>ROC-AUC</span><strong>{forecast.model_verified_roc_auc.toFixed(3)}</strong></div>
      </div>
      <div className={`consistency ${rule?.consistency.includes("consistent") ? "agree" : "review"}`}><i /><div><span>{t(locale, "consistency")}</span><strong>{rule?.consistency?.replaceAll("_", " ") || "unavailable"}</strong></div></div>
      <button className="secondary-button" onClick={onOpen}>{t(locale, "openAnalysis")}<span>→</span></button>
    </aside>
  );
}

function EmptyRun() {
  const { locale } = useApp();
  return <div className="empty-page panel"><span>NO ACTIVE EXERCISE</span><h2>{t(locale, "noSelectedRun")}</h2><Link className="primary-button" to="/console">{t(locale, "console")} →</Link></div>;
}

function RiskMap({ run }: { run: Run }) {
  const { locale } = useApp();
  const canvas = useRef<HTMLCanvasElement>(null);
  const [layer, setLayer] = useState<FieldLayer>("probability");
  const [field, setField] = useState<FieldData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { setField(null); setError(""); api.field(run.id, layer).then(setField).catch((reason) => setError(String(reason))); }, [run.id, layer]);
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
      <div className="panel-label"><span>A / SAUDI GRID FIELD</span><b>{field ? `${field.rows} × ${field.columns}` : "LOADING"}</b></div>
      <div className="layer-switch">
        {(["probability", "rule_risk", "uncertainty"] as FieldLayer[]).map((item) => <button key={item} className={layer === item ? "active" : ""} onClick={() => setLayer(item)}>{item === "probability" ? t(locale, "layerProbability") : item === "rule_risk" ? t(locale, "layerRule") : t(locale, "layerUncertainty")}</button>)}
      </div>
      <div className="map-stage"><canvas ref={canvas} /><div className="grid-lines" /><span className="north">32°N</span><span className="south">16°N</span><span className="west">34°E</span><span className="east">56°E</span>{!field && !error && <div className="map-loading">READING HISTORICAL FIELD</div>}{error && <div className="map-loading error-message">{error}</div>}</div>
      <div className="map-legend"><span>{field?.minimum.toFixed(2) ?? "0.00"}</span><i /><span>{field?.maximum.toFixed(2) ?? "1.00"}</span><small>{field?.cache === "hit" ? "LOCAL CACHE" : "MODEL DERIVED"}</small></div>
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
      <PageHeading eyebrow="EVENT DIAGNOSTICS / 02" title={t(locale, "analysisTitle")} lead={t(locale, "analysisLead")} truth={locale === "zh" ? "模型与规则派生分析" : "Model- and rule-derived analysis"} />
      <section className="analysis-grid">
        <RiskMap run={selectedRun} />
        <article className="metrics-panel panel">
          <div className="panel-label"><span>B / RELIABILITY</span><b>FIXED THRESHOLD</b></div>
          <div className="metric-hero"><span>{cityLabel(locale, forecast.city)} / {hazardLabel(locale, forecast.hazard)}</span><strong>{Math.round(forecast.probability * 100)}<small>%</small></strong><p>{forecast.target_date}</p></div>
          <div className="score-grid">{["pod", "far", "csi", "hss"].map((key) => <div key={key}><span>{key.toUpperCase()}</span><strong>{metrics[key] == null ? "—" : Number(metrics[key]).toFixed(3)}</strong></div>)}</div>
          <div className="boundary-card"><span>INTERPRETATION BOUNDARY</span><p>{locale === "zh" ? "代理标签上的单年时间外推结果，不等同于独立灾害真值或业务可靠性。" : "Single-year temporal holdout over proxy labels; not independent disaster truth or operational reliability."}</p></div>
        </article>
        <article className="indicator-panel panel">
          <div className="panel-label"><span>C / INPUT INDICATORS</span><b>{forecast.features_from_date}</b></div>
          <div className="indicator-table">{Object.entries(indicators).slice(0, 12).map(([name, value]) => <div key={name}><span>{name.replaceAll("_", " ")}</span><strong>{value == null ? "NA" : Number(value).toFixed(2)}</strong></div>)}</div>
        </article>
        <article className="audit-panel panel">
          <div className="panel-label"><span>D / CROSS-CHECK</span><b>{forecast.reflexive_check?.consistency.replaceAll("_", " ")}</b></div>
          <div className="comparison-bars"><div><span>MODEL</span><i style={{ width: `${forecast.probability * 100}%` }} /><strong>{forecast.probability.toFixed(2)}</strong></div><div><span>RULE</span><i style={{ width: `${(forecast.reflexive_check?.detection_engine_risk_score || 0) * 100}%` }} /><strong>{forecast.reflexive_check?.detection_engine_risk_score.toFixed(2)}</strong></div></div>
          <p>{forecast.reflexive_check?.note}</p>
          <div className="fired-list">{forecast.reflexive_check?.detection_engine_conditions_fired.map((item) => <span key={item}>{item}</span>)}</div>
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
          status: "RUN RESULT",
        }
      : indicators.map((name) => ({
          id: `indicator-${name}`,
          type: locale === "zh" ? "观测指标" : "Observed indicator",
          title: name.replaceAll("_", " "),
          description: locale === "zh" ? `来自 ${selectedRun.result?.forecast.features_from_date} 的真实输入指标，作为本次演练的观测依据。` : `A real model input observed on ${selectedRun.result?.forecast.features_from_date}.`,
          status: "OBSERVED",
        })).find((item) => item.id === selectedNode)
        || mechanisms.map((item) => ({
          id: `mechanism-${item.mechanism}`,
          type: locale === "zh" ? "机制断言" : "Mechanism assertion",
          title: item.mechanism.replaceAll("_", " "),
          description: item.description,
          status: item.literature_grounded ? "GROUNDED" : "REVIEW",
        })).find((item) => item.id === selectedNode)
        || citations.map((item) => ({
          id: item.id,
          type: locale === "zh" ? "文献记录" : "Literature record",
          title: item.citation || (locale === "zh" ? "引文记录" : "Citation record"),
          description: item.verification_scope || item.review_status || (locale === "zh" ? "适用范围仍需人工核验。" : "Applicability still requires human review."),
          status: item.review_status || "SCOPE LIMITED",
        })).find((item) => item.id === selectedNode);
  return (
    <>
      <PageHeading eyebrow="EVIDENCE NETWORK / 03" title={t(locale, "evidenceTitle")} lead={locale === "zh" ? "沿着关系线检查本次演练用了哪些观测、机制断言和文献记录；点击任一节点查看来源与核验状态。" : "Trace the observations, mechanism assertions and literature records used for this exercise. Select any node to audit its source and status."} truth={locale === "zh" ? "人工维护证据网络" : "Human-curated evidence network"} />
      <section className="evidence-workspace">
        <article className="network-panel">
          <div className="network-toolbar">
            <div><span>EVENT SUBGRAPH</span><strong>{indicators.length + mechanisms.length + citations.length + 1} NODES · {indicators.length + mechanisms.length + citations.length} EDGES</strong></div>
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
              {indicators.map((item, index) => <button key={item} className={`network-node observation ${selectedNode === `indicator-${item}` ? "selected" : ""}`} style={{ left: "12%", top: `${indicatorY(index) / 5.6}%` }} onClick={() => setSelectedNode(`indicator-${item}`)}><small>INDICATOR</small><strong>{item.replaceAll("_", " ")}</strong></button>)}
              {mechanisms.map((item, index) => <button key={item.mechanism} className={`network-node assertion ${selectedNode === `mechanism-${item.mechanism}` ? "selected" : ""}`} style={{ left: "42%", top: `${mechanismY(index) / 5.6}%` }} onClick={() => setSelectedNode(`mechanism-${item.mechanism}`)}><small>MECHANISM</small><strong>{item.mechanism.replaceAll("_", " ")}</strong></button>)}
              <button className={`network-node hazard ${selectedNode === "hazard" ? "selected" : ""}`} style={{ left: "70%", top: "50%" }} onClick={() => setSelectedNode("hazard")}><small>HAZARD</small><strong>{hazardLabel(locale, evidence.hazard)}</strong><b>{Math.round(selectedRun.result.forecast.probability * 100)}%</b></button>
              {citations.map((item, index) => <button key={item.id} className={`network-node citation ${selectedNode === item.id ? "selected" : ""}`} style={{ left: "89%", top: `${citationY(index) / 5.6}%` }} onClick={() => setSelectedNode(item.id)}><small>CITATION</small><strong>{locale === "zh" ? "文献记录" : "Literature"}</strong></button>)}
            </div>
          </div>
          <div className="network-boundary"><strong>{locale === "zh" ? "关系边界" : "Edge boundary"}</strong><span>{evidence.claim_boundary}</span></div>
        </article>
        <aside className="node-inspector">
          <div className="inspector-heading"><span>NODE INSPECTOR</span><b>{selected?.status}</b></div>
          <div className="inspector-content"><small>{selected?.type}</small><h2>{selected?.title}</h2><p>{selected?.description}</p></div>
          <div className="relation-register">
            <span>{locale === "zh" ? "图中关系" : "Relations in view"}</span>
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
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState<{ content: string; mode: string } | null>(null);
  const [busy, setBusy] = useState(false);
  if (!selectedRun?.result) return <EmptyRun />;
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (!message.trim()) return; setBusy(true);
    try {
      const response = await api.message(selectedRun.id, message, locale);
      setAnswer({ content: response.content, mode: response.mode });
    } finally { setBusy(false); }
  };
  const forecast = selectedRun.result.forecast;
  const decision = selectedRun.result.decision;
  const rule = forecast.reflexive_check;
  const topIndicators = Object.entries(selectedRun.result.conditions.indicators || selectedRun.result.conditions.conditions || {}).filter(([, value]) => value != null).slice(0, 4);
  return (
    <>
      <PageHeading eyebrow="DECISION BRIEF / 04" title={t(locale, "assistantTitle")} lead={locale === "zh" ? "它不是另一个聊天页面：系统把当前演练自动整理成结论、依据、分歧、限制和下一步，方便评委快速理解一次运行。" : "This is not another chat screen. It turns the current run into a conclusion, evidence, disagreement, limitations and next steps."} truth={health?.llm_available ? (locale === "zh" ? "自动简报 + 可选 AI 追问" : "Automatic brief + optional AI") : (locale === "zh" ? "确定性自动简报" : "Deterministic automatic brief")} />
      <section className="brief-workflow">
        <div><span>01</span><p><strong>{locale === "zh" ? "读取运行记录" : "Read run record"}</strong><small>{locale === "zh" ? "概率、指标、阈值" : "Probability, inputs, threshold"}</small></p></div>
        <i>→</i>
        <div><span>02</span><p><strong>{locale === "zh" ? "交叉复核" : "Cross-check"}</strong><small>{locale === "zh" ? "模型、规则、证据" : "Model, rules, evidence"}</small></p></div>
        <i>→</i>
        <div><span>03</span><p><strong>{locale === "zh" ? "形成决策简报" : "Produce brief"}</strong><small>{locale === "zh" ? "结论、限制、下一步" : "Finding, limits, next step"}</small></p></div>
      </section>
      <section className="decision-layout">
        <article className="decision-hero">
          <div className="decision-kicker"><span>HISTORICAL EXERCISE</span><b>{decision.level}</b></div>
          <div className="decision-place"><small>{selectedRun.target_date}</small><h2>{cityLabel(locale, selectedRun.city)} · {hazardLabel(locale, selectedRun.hazard)}</h2></div>
          <div className="decision-probability"><strong>{Math.round(forecast.probability * 100)}</strong><span>%</span><p>{locale === "zh" ? "模型风险概率" : "model risk probability"}</p></div>
          <div className="decision-statement">
            <span>{locale === "zh" ? "一句话结论" : "Bottom line"}</span>
            <p>{locale === "zh" ? `模型超过固定阈值 ${Math.round(decision.threshold * 100)}%，本次历史演练进入 ${decision.level} 等级；仍需结合规则分歧和代理标签边界人工复核。` : `The model exceeds the fixed ${Math.round(decision.threshold * 100)}% threshold and enters the ${decision.level} tier; rule disagreement and proxy-label limits still require review.`}</p>
          </div>
        </article>
        <div className="brief-cards">
          <article><span>A / {locale === "zh" ? "主要依据" : "DRIVERS"}</span><h3>{locale === "zh" ? "前一日输入指标" : "Previous-day indicators"}</h3><div className="driver-list">{topIndicators.map(([name, value]) => <div key={name}><small>{name.replaceAll("_", " ")}</small><strong>{Number(value).toFixed(2)}</strong></div>)}</div><Link to="/analysis">{locale === "zh" ? "查看完整分析" : "Open full analysis"} →</Link></article>
          <article><span>B / {locale === "zh" ? "交叉复核" : "CROSS-CHECK"}</span><h3>{locale === "zh" ? "模型与规则是否一致？" : "Do model and rules agree?"}</h3><div className="crosscheck-score"><div><small>MODEL</small><strong>{forecast.probability.toFixed(2)}</strong></div><i>↔</i><div><small>RULE</small><strong>{rule?.detection_engine_risk_score.toFixed(2) ?? "—"}</strong></div></div><p>{rule?.consistency.replaceAll("_", " ") || "unavailable"}</p><Link to="/evidence">{locale === "zh" ? "沿证据网络核验" : "Audit the evidence network"} →</Link></article>
          <article className="limits-card"><span>C / {locale === "zh" ? "必须说明的限制" : "LIMITS"}</span><h3>{locale === "zh" ? "这个结果能说明什么？" : "What does this result mean?"}</h3><ul><li>{locale === "zh" ? "2025单年历史数据" : "2025 single-year historical data"}</li><li>{locale === "zh" ? "代理标签，不是独立灾情真值" : "Proxy labels, not independent disaster truth"}</li><li>{locale === "zh" ? "历史演练，不是业务预警" : "Historical exercise, not an operational warning"}</li></ul><Link to="/reports">{locale === "zh" ? "生成带边界的报告" : "Generate a bounded report"} →</Link></article>
        </div>
      </section>
      <section className="followup-panel">
        <div className="followup-heading"><div><span>OPTIONAL FOLLOW-UP</span><h2>{locale === "zh" ? "对这份简报继续追问" : "Ask a follow-up about this brief"}</h2></div><b>{health?.llm_available ? "DEEPSEEK AVAILABLE" : (locale === "zh" ? "确定性模板" : "DETERMINISTIC TEMPLATE")}</b></div>
        {answer && <div className="followup-answer"><span>{answer.mode === "deepseek" ? "DEEPSEEK / BOUNDED JSON" : "MAZU / DETERMINISTIC SUMMARY"}</span><p>{answer.content}</p></div>}
        <form onSubmit={submit}><textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder={locale === "zh" ? "例如：为什么模型和规则不一致？" : "For example: Why do model and rules disagree?"} /><button className="primary-button" disabled={busy}>{busy ? "…" : t(locale, "send")}<span>↗</span></button></form>
        <p className="followup-boundary">{locale === "zh" ? "追问只读取当前运行记录，不能修改概率、等级或 CAP。" : "Follow-up only reads the current run; it cannot modify probability, level or CAP."}</p>
      </section>
    </>
  );
}

function ReportsPage() {
  const { locale, selectedRun } = useApp();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [generated, setGenerated] = useState<{ report?: string; evidence?: string; cap?: string; note?: string }>({});
  useEffect(() => { api.reports().then(setReports).catch(() => setReports([])); }, []);
  const createReport = async () => {
    if (!selectedRun) return; const result = await api.createReport(selectedRun.id);
    setGenerated((value) => ({ ...value, report: `/api/v1/artifacts/${result.report.id}`, evidence: `/api/v1/artifacts/${result.evidence.id}` }));
  };
  const createCap = async () => {
    if (!selectedRun) return; const result = await api.cap(selectedRun.id);
    const artifact = result.artifact as { id?: string } | undefined;
    setGenerated((value) => ({ ...value, cap: artifact?.id ? `/api/v1/artifacts/${artifact.id}` : undefined, note: String(result.reason || "") }));
  };
  return (
    <>
      <PageHeading eyebrow="ARTIFACT LIBRARY / 05" title={t(locale, "reportsTitle")} lead={locale === "zh" ? "固定研究材料与每次演练的可下载证据包统一归档。" : "Fixed research materials and run-specific evidence packages in one library."} truth={locale === "zh" ? "运行结果动态生成" : "Generated from run results"} />
      <section className="report-layout">
        <article className="generate-panel panel">
          <div className="panel-label"><span>A / CURRENT EXERCISE</span><b>{selectedRun ? "READY" : "NO RUN"}</b></div>
          {selectedRun?.result ? <><div className="report-run"><span>{selectedRun.target_date}</span><h2>{cityLabel(locale, selectedRun.city)} · {hazardLabel(locale, selectedRun.hazard)}</h2><p>{Math.round(selectedRun.result.forecast.probability * 100)}% · {selectedRun.result.decision.level}</p></div><div className="report-actions"><button className="primary-button" onClick={createReport}>{t(locale, "generateReport")}<span>↓</span></button><button className="secondary-button" onClick={createCap}>{t(locale, "generateCap")}<span>↓</span></button></div>{generated.report && <div className="downloads"><a href={generated.report} target="_blank">HTML / PDF</a><a href={generated.evidence}>JSON EVIDENCE</a>{generated.cap && <a href={generated.cap}>CAP XML</a>}{generated.note && <p>{generated.note}</p>}</div>}</> : <p>{t(locale, "noSelectedRun")}</p>}
        </article>
        <article className="library-panel panel">
          <div className="panel-label"><span>B / DOCUMENT LIBRARY</span><b>{reports.length} ITEMS</b></div>
          <div className="report-list">{reports.map((report) => <a key={report.id} href={report.url} target="_blank" rel="noreferrer"><span>{report.kind.slice(0, 2).toUpperCase()}</span><div><strong>{report.title}</strong><small>{report.kind} · {report.language.toUpperCase()}</small></div><b>↗</b></a>)}</div>
        </article>
      </section>
    </>
  );
}

export default function App() {
  return <AppProvider><Layout><Routes><Route path="/" element={<Navigate to="/console" replace />} /><Route path="/console" element={<ConsolePage />} /><Route path="/analysis" element={<AnalysisPage />} /><Route path="/evidence" element={<EvidencePage />} /><Route path="/assistant" element={<AssistantPage />} /><Route path="/reports" element={<ReportsPage />} /><Route path="*" element={<Navigate to="/console" replace />} /></Routes></Layout></AppProvider>;
}
