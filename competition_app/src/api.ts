import type { Config, FieldData, FieldLayer, Health, Locale, OntologyRelationView, ReportItem, Run, Scenario } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || payload.error || `Request failed (${response.status})`);
  return payload as T;
}

export const api = {
  health: () => request<Health>("/api/v1/health"),
  config: () => request<Config>("/api/v1/config"),
  scenarios: () => request<Scenario[]>("/api/v1/scenarios"),
  runs: () => request<Run[]>("/api/v1/runs"),
  run: (id: string) => request<Run>(`/api/v1/runs/${id}`),
  createRun: (input: { city: string; target_date: string; hazard: string; locale: Locale }) =>
    request<Run>("/api/v1/runs", { method: "POST", body: JSON.stringify(input) }),
  field: (id: string, layer: FieldLayer) =>
    request<FieldData>(`/api/v1/runs/${id}/field?layer=${layer}`),
  cap: (id: string) => request<Record<string, unknown>>(`/api/v1/runs/${id}/cap`, { method: "POST" }),
  message: (id: string, message: string, locale: Locale) =>
    request<{ content: string; mode: string; llm_available: boolean }>("/api/v1/assistant/messages", {
      method: "POST",
      body: JSON.stringify({ run_id: id, message, locale }),
    }),
  reports: () => request<ReportItem[]>("/api/v1/reports"),
  ontologyView: (query = "", module = "") => {
    const params = new URLSearchParams();
    if (query.trim()) params.set("query", query.trim());
    if (module) params.set("module", module);
    const suffix = params.size ? `?${params.toString()}` : "";
    return request<OntologyRelationView>(`/api/v1/ontology/view${suffix}`);
  },
  createReport: (id: string) =>
    request<{ report: { id: string }; evidence: { id: string } }>(`/api/v1/runs/${id}/report`, { method: "POST" }),
};
