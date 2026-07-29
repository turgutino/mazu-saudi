from pathlib import Path


FRONTEND = Path(__file__).parents[1] / "competition_app"


def test_competition_frontend_has_five_routes_and_required_boundaries():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    translations = (FRONTEND / "src" / "i18n.ts").read_text(encoding="utf-8")
    for route in ("/console", "/analysis", "/evidence", "/assistant", "/reports"):
        assert route in app
    for boundary in ("历史演练", "2025 historical data", "Not an operational warning"):
        assert boundary in translations


def test_competition_frontend_excludes_future_research_and_operational_claims():
    public_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (FRONTEND / "src").glob("*")
        if path.suffix in {".ts", ".tsx", ".css"}
    )
    assert "MCR" not in public_sources
    assert "<status>Actual</status>" not in public_sources
    assert '"LIVE"' not in public_sources


def test_competition_frontend_has_no_external_runtime_assets():
    for path in [FRONTEND / "index.html", *list((FRONTEND / "src").glob("*"))]:
        if path.suffix not in {".html", ".ts", ".tsx", ".css"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "https://" not in text
        assert "http://" not in text
