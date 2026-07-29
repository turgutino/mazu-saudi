import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_repository_declares_one_current_product_and_research_assets():
    applications = (ROOT / "APPLICATIONS.md").read_text(encoding="utf-8")
    for required in (
        "唯一比赛入口",
        "competition_app/",
        "src/mazu_saudi/competition/",
        "历史预警研究资产",
        "research/historical_warning/agent/tools.py",
        "非应用",
        "已删除的产品原型",
    ):
        assert required in applications


def test_readme_routes_developers_to_the_application_lifecycle_map():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[应用与运行入口](APPLICATIONS.md)" in readme
    assert "|-- competition_app/" in readme
    assert "|-- research/" in readme
    assert "historical_warning/" in readme
    assert "|   |-- competition/" in readme
    assert "src/mazu_saudi/service/" not in readme


def test_competition_frontend_is_the_only_application_surface():
    assert not (ROOT / "warning_demo").exists()
    assert [path.parent.name for path in ROOT.glob("*/package.json")] == [
        "competition_app"
    ]

    assets = ROOT / "research/historical_warning"
    assert assets.is_dir()
    assert not list(assets.glob("*.html"))
    assert not (assets / "img").exists()
    assert not (assets / "kg/02_make_dashboard.py").exists()
    assert not (assets / "agent/04_make_agent_page.py").exists()


def test_removed_research_product_surface_cannot_be_started_or_packaged():
    assert not (ROOT / "src/mazu_saudi/service").exists()
    assert not (ROOT / "docs/product_interface.md").exists()
    assert not (ROOT / "tests/test_product_service.py").exists()
    assert not (ROOT / "tests/test_product_frontend_contract.py").exists()
    packaging = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "mazu_saudi.service" not in packaging


def test_package_and_research_asset_docs_expose_lifecycle_boundaries():
    competition_init = (ROOT / "src/mazu_saudi/competition/__init__.py").read_text(encoding="utf-8")
    asset_readme = (ROOT / "research/historical_warning/README.md").read_text(encoding="utf-8")
    normalized_asset_readme = " ".join(asset_readme.split())
    assert "primary competition application" in competition_init.lower()
    assert "not an application" in asset_readme
    assert "has no web entry point" in normalized_asset_readme


def test_current_application_code_and_docs_do_not_use_the_retired_demo_name():
    paths = [
        ROOT / "APPLICATIONS.md",
        ROOT / "README.md",
        ROOT / "docs/competition_application.md",
        *sorted((ROOT / "src/mazu_saudi/competition").glob("*.py")),
        ROOT / "scripts/compare_mcr_real_data.py",
    ]
    current_text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "warning_demo" not in current_text
    assert "WARNING_DEMO_" not in current_text


def test_competition_settings_resolve_the_research_asset_tree():
    from mazu_saudi.competition.settings import AppSettings

    settings = AppSettings(repository_root=ROOT, runtime_root=ROOT / "runtime/test")
    assets = ROOT / "research/historical_warning"

    assert settings.research_assets_root == assets
    assert settings.data_file == assets / "data/mazu_dataset.nc"
    assert settings.model_root == assets / "agent/saved_models"
    assert settings.graph_file == assets / "kg/kg_data.json"

    research_python = "\n".join(
        path.read_text(encoding="utf-8") for path in assets.rglob("*.py")
    )
    assert "WARNING_DEMO_" not in research_python
    assert "MAZU_HISTORICAL_DATA_DIR" in research_python


def test_source_tree_has_no_imports_from_the_removed_service():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for root in (ROOT / "src", ROOT / "scripts", ROOT / "tests")
        for path in root.rglob("*.py")
    )
    assert not re.search(
        r"^\s*(?:from|import)\s+mazu_saudi\.service(?:\s|\.|$)",
        sources,
        flags=re.MULTILINE,
    )
