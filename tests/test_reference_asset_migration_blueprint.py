from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = ROOT / "docs" / "reference_asset_migration_blueprint.md"


def test_blueprint_maps_all_reference_asset_families():
    text = BLUEPRINT.read_text(encoding="utf-8")

    required = (
        "LightGBM + 空间传播",
        "XGBoost 迭代工程",
        "IFS + KG 工程",
        "13 区 Agent 工程",
        "GitHub 次日预测",
        "风险研判工程",
        "生产实习工程",
        "计科 2304 工程",
    )
    for name in required:
        assert name in text


def test_blueprint_separates_science_baselines_artifacts_and_service():
    text = BLUEPRINT.read_text(encoding="utf-8")

    for boundary in (
        "baselines/",
        "mcr_precip/",
        "artifacts/",
        "delivery/",
        "ForecastBackend",
        "FrozenArtifactForecastBackend",
        "不会成为第五、第六个 MCR 专家",
    ):
        assert boundary in text


def test_blueprint_preserves_causal_and_clean_room_rules():
    text = BLUEPRINT.read_text(encoding="utf-8")

    for rule in (
        "clean-room",
        "not_observable",
        "测试集禁止搜索",
        "训练折生成",
        "最终测试",
        "Experiment Lock",
        "Forecast Artifact",
        "Evaluation Artifact",
        "Report Artifact",
    ):
        assert rule in text


def test_blueprint_has_incremental_slices_and_repo_links():
    text = BLUEPRINT.read_text(encoding="utf-8")

    for number in range(1, 6):
        assert f"### Slice {number}：" in text

    assert "Slice 1：实验骨架" in text
    assert "(adr/0005-treat-reference-projects-as-design-inputs.md)" in text
    assert "reference_asset_migration_blueprint.md" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "reference_asset_migration_blueprint.md" in (
        ROOT / "docs" / "own_warning_framework.md"
    ).read_text(encoding="utf-8")
