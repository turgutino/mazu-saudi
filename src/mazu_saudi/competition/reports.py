"""Printable bilingual reports and report-library metadata."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any


REPORT_LIBRARY = [
    {
        "id": "midterm-en",
        "title": "MAZU Mid-Term Report",
        "language": "en",
        "kind": "research",
        "url": "/legacy/reports/MAZU_MidTerm_Report_EN.pdf",
    },
    {
        "id": "midterm-zh",
        "title": "MAZU 中期报告",
        "language": "zh",
        "kind": "research",
        "url": "/legacy/reports/MAZU_MidTerm_Report_CN.pdf",
    },
    {
        "id": "verification-en",
        "title": "Real-Event Verification Report",
        "language": "en",
        "kind": "verification",
        "url": "/legacy/reports/MAZU_Real_Hadise_Dogrulama_EN.pdf",
    },
    {
        "id": "verification-zh",
        "title": "真实事件核验报告",
        "language": "zh",
        "kind": "verification",
        "url": "/legacy/reports/MAZU_Real_Hadise_Dogrulama_CN.pdf",
    },
    {
        "id": "legacy-story",
        "title": "Legacy Research Showcase",
        "language": "en",
        "kind": "archive",
        "url": "/legacy/index.html",
    },
]


def render_run_report(run: dict[str, Any]) -> str:
    result = run["result"]
    forecast = result["forecast"]
    consistency = forecast.get("reflexive_check") or {}
    metrics = forecast.get("meteorological_metrics") or {}
    uncertainty = forecast.get("uncertainty") or {}
    title = f"{forecast['city']} · {forecast['hazard']} · {forecast['target_date']}"
    rows = [
        ("Target date / 目标日期", forecast["target_date"]),
        ("Input date / 输入日期", forecast["features_from_date"]),
        ("Probability / 风险概率", f"{forecast['probability']:.1%}"),
        ("Level / 风险等级", result["decision"]["level"]),
        ("Rule score / 规则风险分", f"{consistency.get('detection_engine_risk_score', 0):.2f}"),
        ("Consistency / 一致性", consistency.get("consistency", "unavailable")),
        ("Ensemble spread / 集合分歧", uncertainty.get("std", "unavailable")),
        ("POD", metrics.get("pod", "unavailable")),
        ("FAR", metrics.get("far", "unavailable")),
        ("CSI", metrics.get("csi", "unavailable")),
        ("HSS", metrics.get("hss", "unavailable")),
    ]
    table = "".join(
        f"<tr><th>{escape(str(label))}</th><td>{escape(str(value))}</td></tr>"
        for label, value in rows
    )
    indicators = result["conditions"].get("conditions") or result["conditions"].get("indicators") or {}
    indicator_rows = "".join(
        f"<tr><th>{escape(str(name))}</th><td>{escape(str(value))}</td></tr>"
        for name, value in list(indicators.items())[:18]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(title)} — MAZU Historical Exercise</title>
<style>
body{{font:15px/1.55 system-ui,sans-serif;color:#17231f;max-width:900px;margin:48px auto;padding:0 28px}}
h1{{font-size:30px;margin-bottom:4px}} .boundary{{padding:14px 18px;background:#fff4d6;border-left:4px solid #d18b17}}
table{{border-collapse:collapse;width:100%;margin:18px 0 32px}}th,td{{padding:10px;border-bottom:1px solid #d9e2de;text-align:left}}
th{{width:42%;color:#456159}}footer{{margin-top:48px;color:#61756f}}@media print{{button{{display:none}}body{{margin:0}}}}
</style></head><body>
<button onclick="window.print()">Print / Save as PDF</button>
<p>MAZU Saudi Historical Warning Console</p><h1>{escape(title)}</h1>
<p class="boundary"><strong>Historical Exercise / 历史演练</strong><br>
2025 historical data · Not an operational warning · Proxy-label model, not independent disaster truth.</p>
<h2>Warning summary / 预警摘要</h2><table>{table}</table>
<h2>Input indicators / 输入指标</h2><table>{indicator_rows or '<tr><td>No indicator payload</td></tr>'}</table>
<h2>Evidence boundary / 证据边界</h2>
<p>{escape(result['evidence'].get('claim_boundary', 'Evidence graph supports explanation only.'))}</p>
<footer>Run ID: {escape(run['id'])} · Created: {escape(run['created_at'])}</footer>
</body></html>"""


def render_evidence_json(run: dict[str, Any]) -> str:
    return json.dumps(
        {
            "schema_version": "mazu-historical-evidence-v1",
            "historical_exercise": True,
            "operational_warning": False,
            "run": run,
        },
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )
