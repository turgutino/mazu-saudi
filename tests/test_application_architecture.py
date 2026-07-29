import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_repository_declares_one_current_product_and_one_legacy_surface():
    applications = (ROOT / "APPLICATIONS.md").read_text(encoding="utf-8")
    for required in (
        "唯一比赛入口",
        "competition_app/",
        "src/mazu_saudi/competition/",
        "Legacy Archive",
        "warning_demo/agent/tools.py",
        "已删除的产品原型",
    ):
        assert required in applications


def test_readme_routes_developers_to_the_application_lifecycle_map():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[应用与运行入口](APPLICATIONS.md)" in readme
    assert "|-- competition_app/" in readme
    assert "|   |-- competition/" in readme
    assert "src/mazu_saudi/service/" not in readme


def test_removed_research_product_surface_cannot_be_started_or_packaged():
    assert not (ROOT / "src/mazu_saudi/service").exists()
    assert not (ROOT / "docs/product_interface.md").exists()
    assert not (ROOT / "tests/test_product_service.py").exists()
    assert not (ROOT / "tests/test_product_frontend_contract.py").exists()
    packaging = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "mazu_saudi.service" not in packaging


def test_package_and_legacy_docs_expose_lifecycle_boundaries():
    competition_init = (ROOT / "src/mazu_saudi/competition/__init__.py").read_text(encoding="utf-8")
    legacy_readme = (ROOT / "warning_demo/README.md").read_text(encoding="utf-8")
    assert "primary competition application" in competition_init.lower()
    assert "Legacy Archive" in legacy_readme


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
