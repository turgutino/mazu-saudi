"""Application use cases for historical warning exercises."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import request as urllib_request

from .adapters import HistoricalToolAdapter, WarningAdapter, finite_json, level_for_probability
from .settings import AppSettings
from .storage import AuditStore


SCENARIOS = [
    {
        "id": "heatwave-mecca",
        "city": "Mecca",
        "target_date": "2025-08-04",
        "hazard": "heatwave",
        "kind": "strong_case",
        "title_en": "Mecca heatwave signal",
        "title_zh": "麦加高温信号",
    },
    {
        "id": "dust-dammam",
        "city": "Dammam",
        "target_date": "2025-07-06",
        "hazard": "dust_storm",
        "kind": "high_risk",
        "title_en": "Dammam Shamal dust risk",
        "title_zh": "达曼夏季沙马尔风沙尘风险",
    },
    {
        "id": "flood-jizan-mismatch",
        "city": "Jizan",
        "target_date": "2025-08-23",
        "hazard": "flash_flood",
        "kind": "review_case",
        "title_en": "Jizan model–rule mismatch",
        "title_zh": "吉赞模型—规则不一致案例",
    },
    {
        "id": "calm-riyadh",
        "city": "Riyadh",
        "target_date": "2025-02-10",
        "hazard": "dust_storm",
        "kind": "negative_control",
        "title_en": "Riyadh calm-day control",
        "title_zh": "利雅得平稳日负对照",
    },
]


class HistoricalWarningService:
    def __init__(
        self,
        settings: AppSettings,
        store: AuditStore,
        adapter: WarningAdapter | None = None,
    ):
        self.settings = settings
        self.store = store
        self.adapter = adapter or HistoricalToolAdapter(settings)

    def create_run(self, city: str, target_date: str, hazard: str, locale: str) -> dict[str, Any]:
        preflight = self.settings.preflight()
        if not preflight["ready_for_inference"]:
            raise RuntimeError(
                "Archive mode: inference disabled because required assets are missing: "
                + ", ".join(preflight["missing"])
            )
        run_id = self.store.create_run(city, target_date, hazard, locale)
        try:
            forecast = self.adapter.forecast(city, target_date, hazard)
            conditions = self.adapter.conditions(city, forecast["features_from_date"])
            evidence = self.adapter.evidence(hazard)
            tools = getattr(self.adapter, "_load_tools", lambda: None)()
            if tools is not None:
                level, threshold = level_for_probability(tools, hazard, forecast["probability"])
            else:
                threshold = 0.55 if hazard != "flash_flood" else 0.5
                level = "elevated" if forecast["probability"] >= threshold else "low"
            result = finite_json(
                {
                    "contract_version": "historical-run-v1",
                    "mode": "historical_exercise",
                    "operational_warning": False,
                    "scientific_evidence": "single-year-proxy-only",
                    "forecast": forecast,
                    "conditions": conditions,
                    "evidence": evidence,
                    "decision": {
                        "level": level,
                        "threshold": threshold,
                        "alert_candidate": forecast["probability"] >= threshold,
                        "policy": "existing fixed hazard threshold",
                    },
                    "versions": {
                        "model": "warning-demo-production-v1",
                        "dataset": "saudi-2025-indicators",
                        "evidence_graph": "auditable-evidence-graph-v2",
                    },
                    "boundaries": [
                        "Historical Exercise / 历史演练",
                        "2025 historical data",
                        "Not an operational warning",
                        "Proxy labels are not independent disaster truth",
                    ],
                }
            )
            self.store.complete_run(run_id, result)
        except Exception as exc:
            self.store.fail_run(run_id, str(exc))
            raise
        return self.store.get_run(run_id)

    def deterministic_analysis(self, run: dict[str, Any], locale: str) -> str:
        result = run["result"]
        forecast = result["forecast"]
        reflexive = forecast.get("reflexive_check") or {}
        uncertainty = forecast.get("uncertainty") or {}
        if locale == "en":
            return (
                f"{forecast['city']} has a {forecast['probability']:.1%} historical "
                f"{forecast['hazard']} risk for {forecast['target_date']}, using indicators "
                f"available on {forecast['features_from_date']}. Model–rule status: "
                f"{reflexive.get('consistency', 'unavailable')}; ensemble spread: "
                f"{uncertainty.get('std', 'unavailable')}. This is a 2025 historical "
                "exercise based on proxy labels, not an operational warning."
            )
        return (
            f"{forecast['city']} 在 {forecast['target_date']} 的历史"
            f"{forecast['hazard']}风险为 {forecast['probability']:.1%}，输入来自"
            f"{forecast['features_from_date']}。模型—规则状态："
            f"{reflexive.get('consistency', '不可用')}；集合分歧："
            f"{uncertainty.get('std', '不可用')}。这是基于代理标签的2025历史演练，"
            "不是业务预警。"
        )

    def assistant_response(
        self, run: dict[str, Any], message: str, locale: str
    ) -> tuple[str, str]:
        fallback = self.deterministic_analysis(run, locale)
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            return fallback, "deterministic"
        result = run["result"]
        compact_context = {
            "forecast": result["forecast"],
            "decision": result["decision"],
            "conditions": result["conditions"],
            "evidence": result["evidence"],
            "boundaries": result["boundaries"],
        }
        system = (
            "You are the bounded analysis layer of a 2025 historical weather-warning "
            "exercise. Answer only from the supplied frozen JSON. Never change forecast "
            "values, invent mechanisms, call this an operational warning, or treat proxy "
            "labels as independent disaster truth. Explicitly preserve uncertainty and "
            "evidence-review boundaries. Respond in Chinese."
            if locale == "zh"
            else
            "You are the bounded analysis layer of a 2025 historical weather-warning "
            "exercise. Answer only from the supplied frozen JSON. Never change forecast "
            "values, invent mechanisms, call this an operational warning, or treat proxy "
            "labels as independent disaster truth. Explicitly preserve uncertainty and "
            "evidence-review boundaries. Respond in English."
        )
        payload = json.dumps(
            {
                "model": "deepseek-chat",
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": f"Frozen result:\n{json.dumps(compact_context, ensure_ascii=False)}\n\nQuestion:\n{message}",
                    },
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        outbound = urllib_request.Request(
            "https://api.deepseek.com/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(outbound, timeout=20) as response:
                parsed = json.loads(response.read().decode("utf-8"))
            content = parsed["choices"][0]["message"]["content"].strip()
            return content or fallback, "deepseek"
        except Exception:
            return fallback, "deterministic_fallback"
