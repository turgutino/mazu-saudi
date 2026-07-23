from pathlib import Path

from mazu_saudi.service import server


def test_frontend_surfaces_reliability_and_demo_boundaries():
    html = (server.ASSET_ROOT / "index.html").read_text(encoding="utf-8")
    required = ["+01H", "+03H", "+06H", "机制贡献", "数据可用性", "DEMO", "非业务预报", "Scientific evidence"]
    for text in required:
        assert text in html
    assert "region_id_used_by_router" not in html


def test_frontend_has_no_external_runtime_dependencies():
    for name in ("index.html", "styles.css", "app.js"):
        text = (server.ASSET_ROOT / name).read_text(encoding="utf-8")
        assert "https://" not in text
        assert "http://" not in text
