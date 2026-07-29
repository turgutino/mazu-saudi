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

function PageHeading({ eyebrow, title, lead }: { eyebrow: string; title: string; lead: string }) {
  return <header className="page-heading"><span>{eyebrow}</span><h1>{title}</h1><p>{lead}</p></header>;
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
      <PageHeading eyebrow="WARNING WORKFLOW / 01" title={t(locale, "selectTask")} lead={t(locale, "selectTaskLead")} />
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
      <PageHeading eyebrow="EVENT DIAGNOSTICS / 02" title={t(locale, "analysisTitle")} lead={t(locale, "analysisLead")} />
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
  if (!selectedRun?.result) return <EmptyRun />;
  const evidence = selectedRun.result.evidence;
  return (
    <>
      <PageHeading eyebrow="EVIDENCE AUDIT / 03" title={t(locale, "evidenceTitle")} lead={evidence.claim_boundary} />
      <section className="evidence-layout">
        <article className="graph-panel panel">
          <div className="panel-label"><span>A / EVENT SUBGRAPH</span><b>EXPLANATION ONLY</b></div>
          <div className="evidence-graph">
            <div className="graph-center"><span>HAZARD</span><strong>{hazardLabel(locale, evidence.hazard)}</strong></div>
            <div className="graph-ring mechanisms">{evidence.mechanisms.slice(0, 5).map((item, index) => <div key={item.mechanism} style={{ "--i": index, "--n": Math.min(5, evidence.mechanisms.length) } as React.CSSProperties}><span>M</span><strong>{item.mechanism.replaceAll("_", " ")}</strong></div>)}</div>
            <div className="graph-ring indicators">{evidence.contributing_indicators.slice(0, 7).map((item, index) => <div key={item} style={{ "--i": index, "--n": Math.min(7, evidence.contributing_indicators.length) } as React.CSSProperties}><span>I</span><strong>{item.replaceAll("_", " ")}</strong></div>)}</div>
          </div>
          <div className="graph-legend"><span><i className="mechanism-dot" />Mechanism assertion</span><span><i className="indicator-dot" />Observed indicator</span><span><i className="citation-dot" />Literature record</span></div>
        </article>
        <aside className="evidence-list panel">
          <div className="panel-label"><span>B / EVIDENCE REGISTER</span><b>{evidence.mechanisms.length} MECHANISMS</b></div>
          {evidence.mechanisms.map((item) => <details key={item.mechanism}><summary><span><i className={item.literature_grounded ? "grounded" : ""} /><strong>{item.mechanism.replaceAll("_", " ")}</strong></span><b>{item.literature_grounded ? "GROUNDED" : "REVIEW"}</b></summary><p>{item.description}</p>{item.citations.map((citation, index) => <a key={index} href={citation.url} target="_blank" rel="noreferrer">{citation.citation || "Citation record"}<small>{citation.review_status || "scope limited"}</small></a>)}</details>)}
        </aside>
      </section>
    </>
  );
}

function AssistantPage() {
  const { locale, selectedRun } = useApp();
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  if (!selectedRun?.result) return <EmptyRun />;
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (!message.trim()) return; setBusy(true);
    try { setAnswer((await api.message(selectedRun.id, message, locale)).content); } finally { setBusy(false); }
  };
  return (
    <>
      <PageHeading eyebrow="BOUNDED ASSISTANT / 04" title={t(locale, "assistantTitle")} lead={locale === "zh" ? "核心分析由确定性工具生成；网络不可用也不会影响预测结果。" : "Core analysis is deterministic. Network availability never changes forecast values."} />
      <section className="assistant-layout panel">
        <div className="assistant-context"><span>ACTIVE EXERCISE</span><h2>{cityLabel(locale, selectedRun.city)} · {hazardLabel(locale, selectedRun.hazard)}</h2><p>{selectedRun.target_date}</p><div><strong>{Math.round(selectedRun.result.forecast.probability * 100)}%</strong><small>{t(locale, "probability")}</small></div></div>
        <div className="conversation">
          <div className="assistant-message"><span>MAZU / TOOL ANALYSIS</span><p>{answer || (locale === "zh" ? "我只分析当前冻结的预测、指标和证据，不会修改模型结果。你可以询问风险原因、可靠性或CAP含义。" : "I only analyze this frozen forecast, its indicators and evidence. Ask about drivers, reliability or CAP semantics.")}</p></div>
          <form onSubmit={submit}><textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder={t(locale, "ask")} /><button className="primary-button" disabled={busy}>{busy ? "…" : t(locale, "send")}<span>↗</span></button></form>
          <div className="prompt-chips">{[locale === "zh" ? "为什么模型和规则不一致？" : "Why do model and rules disagree?", locale === "zh" ? "这个概率可靠吗？" : "Is this probability reliable?", locale === "zh" ? "解释主要指标" : "Explain the main indicators"].map((item) => <button key={item} onClick={() => setMessage(item)}>{item}</button>)}</div>
        </div>
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
      <PageHeading eyebrow="ARTIFACT LIBRARY / 05" title={t(locale, "reportsTitle")} lead={locale === "zh" ? "固定研究材料与每次演练的可下载证据包统一归档。" : "Fixed research materials and run-specific evidence packages in one library."} />
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
