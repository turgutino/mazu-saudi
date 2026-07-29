from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs" / "reference_projects_review.md"


def test_new_reference_projects_are_audited():
    text = REVIEW.read_text(encoding="utf-8")

    for project in (
        "沙特极端天气风险研判",
        "生产实习最终报告-郭展宏-2023040087-翁联桥-2023040088",
        "计科2304-2023040319-夏祥麟",
    ):
        assert project in text


def test_review_preserves_scientific_integrity_boundaries():
    text = REVIEW.read_text(encoding="utf-8")

    required = (
        "not_observable",
        "预注册",
        "测试集污染",
        "未来事件",
        "被留出的事件",
        "训练折内部生成",
        "最终测试集只评一次",
        "不复制源码",
    )
    for phrase in required:
        assert phrase in text


def test_review_maps_reusable_assets_to_own_framework():
    text = REVIEW.read_text(encoding="utf-8")

    for asset in (
        "ForecastArtifact",
        "EvaluationArtifact",
        "ReportArtifact",
        "Analog Ensemble",
        "机制原型",
        "MCR-Precip",
        "未来制品服务",
    ):
        assert asset in text

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "八个参考工程" in readme
    assert "(docs/reference_projects_review.md)" in readme
