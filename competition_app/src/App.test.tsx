import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const health = {
  status: "ok",
  mode: "historical_exercise",
  ready_for_inference: true,
  checks: { dataset: true, models: true },
  missing: [],
  llm_available: false,
};
const config = {
  product: { name: "MAZU Saudi Historical Warning Console", name_zh: "MAZU 沙特历史预警演练台" },
  cities: ["Mecca", "Jizan"],
  hazards: ["heatwave", "flash_flood"],
  date_range: { start: "2025-01-02", end: "2025-12-31" },
  mode: "historical_exercise",
  boundaries: ["Historical Exercise / 历史演练", "Not an operational warning"],
};
const scenario = {
  id: "heatwave-mecca",
  city: "Mecca",
  target_date: "2025-08-04",
  hazard: "heatwave",
  kind: "strong_case",
  title_en: "Mecca heatwave signal",
  title_zh: "麦加高温信号",
};
const run = {
  id: "run-1",
  city: "Mecca",
  target_date: "2025-08-04",
  hazard: "heatwave",
  locale: "zh",
  status: "complete",
  created_at: "2026-07-29T00:00:00Z",
  error: null,
  result: {
    contract_version: "historical-run-v1",
    mode: "historical_exercise",
    operational_warning: false,
    scientific_evidence: "single-year-proxy-only",
    forecast: {
      city: "Mecca",
      target_date: "2025-08-04",
      features_from_date: "2025-08-03",
      hazard: "heatwave",
      probability: 0.8985,
      grid_cell: { lat: 21.4, lon: 39.8 },
      elevation_m: 310,
      terrain_note: null,
      impact_context: null,
      reflexive_check: {
        detection_engine_risk_score: 0.2,
        detection_engine_conditions_fired: [],
        consistency: "model_higher_than_detection",
      },
      model_verified_roc_auc: 0.971,
      meteorological_metrics: { pod: 0.77, far: 0.18, csi: 0.68, hss: 0.79 },
      uncertainty: { mean: 0.88, std: 0.04, range: [0.8, 0.93], n_members: 5 },
    },
    conditions: { city: "Mecca", date: "2025-08-03", indicators: { tmax_c: 44.05 } },
    evidence: {
      hazard: "heatwave",
      claim_boundary: "Explanation only.",
      contributing_indicators: ["tmax_c"],
      mechanisms: [],
    },
    decision: { level: "emergency", threshold: 0.55, alert_candidate: true, policy: "fixed" },
    boundaries: ["Historical Exercise / 历史演练"],
  },
};
const ontologyGraph = {
  ontology: {
    ontology_iri: "urn:mazu-saudi:ontology",
    version: "1.0.0",
    source_sha256: "abc123",
    loaded_at: "2026-07-29T00:00:00Z",
  },
  filters: { query: "", module: null },
  nodes: [
    {
      iri: "urn:mazu-saudi:concept:HighIVTState",
      local_name: "HighIVTState",
      resource_type: "urn:mazu-saudi:ontology:IndicatorState",
      module: "state",
      status: null,
      label: "高水汽输送状态",
      label_en: "High IVT state",
      label_zh: "高水汽输送状态",
      definition_en: "A versioned high IVT state.",
      definition_zh: "通过版本化阈值定义的高水汽输送状态。",
    },
    {
      iri: "urn:mazu-saudi:concept:IntegratedVaporTransport",
      local_name: "IntegratedVaporTransport",
      resource_type: "urn:mazu-saudi:ontology:MeteorologicalIndicator",
      module: "indicator",
      status: null,
      label: "整层水汽输送",
      label_en: "Integrated vapor transport",
      label_zh: "整层水汽输送",
      definition_en: "Vertically integrated vapor transport.",
      definition_zh: "垂直积分水汽输送指标。",
    },
  ],
  edges: [{
    id: 1,
    source: "urn:mazu-saudi:concept:HighIVTState",
    target: "urn:mazu-saudi:concept:IntegratedVaporTransport",
    predicate: "urn:mazu-saudi:ontology:derivedFromIndicator",
    predicate_label: "derivedFromIndicator",
  }],
  node_count: 2,
  edge_count: 1,
};

function jsonResponse(payload: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  }));
}

describe("historical warning application", () => {
  let created = false;
  beforeEach(() => {
    created = false;
    localStorage.clear();
    window.history.pushState({}, "", "/console");
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/v1/health") return jsonResponse(health);
      if (path === "/api/v1/config") return jsonResponse(config);
      if (path === "/api/v1/scenarios") return jsonResponse([scenario]);
      if (path === "/api/v1/runs" && init?.method === "POST") {
        created = true;
        return jsonResponse(run, 201);
      }
      if (path === "/api/v1/runs") return jsonResponse(created ? [run] : []);
      if (path.startsWith("/api/v1/ontology/view")) return jsonResponse(ontologyGraph);
      throw new Error(`Unhandled request: ${path}`);
    }));
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders the application task flow and boundary", async () => {
    render(<BrowserRouter><App /></BrowserRouter>);
    expect(await screen.findByText("历史预警演练")).toBeInTheDocument();
    expect(screen.getByText("2025历史数据 · 非业务预警")).toBeInTheDocument();
    expect(await screen.findByText("麦加高温信号")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /运行风险评估/ })).toBeEnabled();
  });

  it("creates a run and renders a risk bulletin", async () => {
    render(<BrowserRouter><App /></BrowserRouter>);
    fireEvent.click(await screen.findByRole("button", { name: /运行风险评估/ }));
    await waitFor(() => expect(screen.getByText("90")).toBeInTheDocument());
    expect(screen.getByText("模型高于规则")).toBeInTheDocument();
    expect(screen.queryByText("model higher than detection")).not.toBeInTheDocument();
    expect(localStorage.getItem("mazu-run")).toBe("run-1");
  });

  it("switches the primary interface to English", async () => {
    render(<BrowserRouter><App /></BrowserRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "EN" }));
    expect(screen.getByText("Historical warning exercise")).toBeInTheDocument();
    expect(screen.getByText("2025 historical data · Not an operational warning")).toBeInTheDocument();
    expect(screen.getByText(/Task control/)).toBeInTheDocument();
    expect(screen.getByText("Curated / audited")).toBeInTheDocument();
    expect(screen.queryByText("任务控制")).not.toBeInTheDocument();
    expect(screen.queryByText("精选 / 已核验")).not.toBeInTheDocument();
  });

  it("browses the live ontology service and inspects a node", async () => {
    window.history.pushState({}, "", "/ontology");
    render(<BrowserRouter><App /></BrowserRouter>);

    expect(await screen.findByRole("heading", { name: "天气机制本体" })).toBeInTheDocument();
    expect(await screen.findByText(/2 本体资源 · 1 结构关系/)).toBeInTheDocument();
    const highIvtNode = await screen.findByRole("button", { name: "高水汽输送状态" });
    expect(document.querySelectorAll(".kg-node-label")).toHaveLength(2);
    expect(document.querySelector("#ontology-arrow")).toBeInTheDocument();
    fireEvent.click(highIvtNode);
    expect(screen.getByText("通过版本化阈值定义的高水汽输送状态。")).toBeInTheDocument();
    expect(screen.getAllByText("derivedFromIndicator").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByRole("textbox", { name: /搜索中英文名称或定义/ }), {
      target: { value: "IVT" },
    });
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith("/api/v1/ontology/view?query=IVT", expect.anything());
    });
  });

  it("keeps the future knowledge graph separate from the ontology", async () => {
    window.history.pushState({}, "", "/knowledge-graph");
    render(<BrowserRouter><App /></BrowserRouter>);

    expect(await screen.findByText("全球观测机制适用性知识图谱")).toBeInTheDocument();
    expect(screen.getByText("知识图谱尚未构建")).toBeInTheDocument();
    expect(screen.getByText(/当前只有本体定义/)).toBeInTheDocument();
    expect(screen.queryByText(/2 本体资源/)).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/ontology/view"),
      expect.anything(),
    );
  });
});
