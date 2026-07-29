from pathlib import Path

from mazu_saudi.service import server as research_server


ROOT = Path(__file__).parents[1]


def test_repository_declares_one_current_product_and_two_non_product_surfaces():
    applications = (ROOT / "APPLICATIONS.md").read_text(encoding="utf-8")
    for required in (
        "唯一比赛入口",
        "competition_app/",
        "src/mazu_saudi/competition/",
        "冻结的研究原型",
        "Legacy Archive",
        "warning_demo/agent/tools.py",
    ):
        assert required in applications


def test_readme_routes_developers_to_the_application_lifecycle_map():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[应用与运行入口](APPLICATIONS.md)" in readme
    assert "|-- competition_app/" in readme
    assert "|   |-- competition/" in readme
    assert "|   `-- service/" in readme


def test_research_prototype_does_not_compete_for_the_product_port():
    applications = (ROOT / "APPLICATIONS.md").read_text(encoding="utf-8")
    competition_start = (ROOT / "scripts/start_competition_app.sh").read_text(encoding="utf-8")
    assert 'APP_PORT="${MAZU_APP_PORT:-8765}"' in competition_start
    assert research_server.DEFAULT_PORT == 8766
    assert "--port 8766" in applications


def test_package_and_legacy_docs_expose_lifecycle_boundaries():
    competition_init = (ROOT / "src/mazu_saudi/competition/__init__.py").read_text(encoding="utf-8")
    research_init = (ROOT / "src/mazu_saudi/service/__init__.py").read_text(encoding="utf-8")
    legacy_readme = (ROOT / "warning_demo/README.md").read_text(encoding="utf-8")
    assert "primary competition application" in competition_init.lower()
    assert "frozen research prototype" in research_init.lower()
    assert "Legacy Archive" in legacy_readme
