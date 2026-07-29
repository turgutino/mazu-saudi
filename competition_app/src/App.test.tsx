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
    expect(screen.getByText("model higher than detection")).toBeInTheDocument();
    expect(localStorage.getItem("mazu-run")).toBe("run-1");
  });

  it("switches the primary interface to English", async () => {
    render(<BrowserRouter><App /></BrowserRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "EN" }));
    expect(screen.getByText("Historical warning exercise")).toBeInTheDocument();
    expect(screen.getByText("2025 historical data · Not an operational warning")).toBeInTheDocument();
  });
});
