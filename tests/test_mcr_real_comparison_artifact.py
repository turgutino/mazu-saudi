import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "mcr_precip_2025_proxy" / "results.json"
REPORT = ROOT / "experiments" / "mcr_precip_2025_proxy" / "report.md"


def _assert_finite_json(value):
    if isinstance(value, dict):
        for item in value.values():
            _assert_finite_json(item)
    elif isinstance(value, list):
        for item in value:
            _assert_finite_json(item)
    elif isinstance(value, float):
        assert math.isfinite(value)


def test_real_comparison_artifact_freezes_protocol_and_negative_decision():
    result = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert result["schema_version"] == "mcr-proxy-comparison-v1"
    assert result["scientific_evidence"] == "single-year-proxy-only"
    assert result["protocol"]["threshold_source"] == "validation"
    assert result["protocol"]["test_tuned"] is False
    assert result["protocol"]["seeds"] == [42, 43, 44]
    assert result["decision"]["status"] == "research_only_not_adopted"
    assert result["decision"]["adopt_mcr_as_competition_performance_claim"] is False
    assert result["decision"]["mechanism_prior_supported_in_this_experiment"] is False
    assert result["decision"]["paired_seed_pr_auc_wins_vs_hgb"] == [False, False, False]
    _assert_finite_json(result)


def test_artifact_does_not_hide_mcr_underperformance():
    result = json.loads(RESULTS.read_text(encoding="utf-8"))
    hgb = result["models"]["hgb_matched"]["summary"]
    mcr = result["models"]["mcr_prior"]["summary"]
    assert hgb["pr_auc"]["mean"] > mcr["pr_auc"]["mean"]
    assert hgb["brier"]["mean"] < mcr["brier"]["mean"]
    assert mcr["far"]["mean"] > 0.9
    report = REPORT.read_text(encoding="utf-8")
    normalized_report = " ".join(report.split())
    assert "not an" in normalized_report
    assert "independent flash-flood truth evaluation" in normalized_report
    assert "research_only_not_adopted" in report
