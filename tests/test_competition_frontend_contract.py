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


def test_competition_frontend_uses_light_service_workspace_visual_system():
    styles = (FRONTEND / "src" / "styles.css").read_text(encoding="utf-8")
    assert "color-scheme: light" in styles
    assert "--canvas: #f4f7f7" in styles
    assert "--navy: #173f6b" in styles
    assert 'grid-template-areas: "controls brief" "scenarios brief"' in styles
    assert "background: #061712" not in styles


def test_competition_frontend_explains_truth_layers_and_assistant_mode():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    translations = (FRONTEND / "src" / "i18n.ts").read_text(encoding="utf-8")
    for boundary in (
        "本地模型按次重算",
        "模型与规则派生分析",
        "人工维护证据网络",
        "确定性自动简报",
        "运行结果动态生成",
    ):
        assert boundary in app
    assert "代理标签验证" in app
    assert "追问只读取当前运行记录" in app
    assert "不能修改概率、等级或 CAP" in app
    assert 'assistant: "决策简报"' in translations


def test_evidence_page_renders_relationship_network_and_node_inspector():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    styles = (FRONTEND / "src" / "styles.css").read_text(encoding="utf-8")
    for contract in ("observation-edge", "mechanism-edge", "citation-edge", "NODE INSPECTOR"):
        assert contract in app
    assert "network-canvas" in styles
    assert "graph-ring" not in app


def test_decision_brief_is_primary_and_follow_up_is_optional():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    for section in ("一句话结论", "主要依据", "交叉复核", "必须说明的限制", "OPTIONAL FOLLOW-UP"):
        assert section in app
