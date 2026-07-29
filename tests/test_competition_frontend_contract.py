from pathlib import Path


FRONTEND = Path(__file__).parents[1] / "competition_app"


def test_competition_frontend_has_five_routes_and_required_boundaries():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    translations = (FRONTEND / "src" / "i18n.ts").read_text(encoding="utf-8")
    for route in ("/console", "/analysis", "/evidence", "/assistant", "/reports"):
        assert route in app
    for boundary in ("历史演练", "2025 historical data", "Not an operational warning"):
        assert boundary in translations


def test_competition_frontend_has_overview_and_knowledge_graph_routes():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    translations = (FRONTEND / "src" / "i18n.ts").read_text(encoding="utf-8")
    vite_config = (FRONTEND / "vite.config.ts").read_text(encoding="utf-8")
    assert "/overview" in app
    assert "/knowledge-graph" in app
    for source in (app, translations, vite_config):
        assert "/legacy" not in source


def test_knowledge_graph_reads_the_versioned_ontology_service():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    api = (FRONTEND / "src" / "api.ts").read_text(encoding="utf-8")
    types = (FRONTEND / "src" / "types.ts").read_text(encoding="utf-8")

    assert "api.ontologyGraph(search, module)" in app
    assert 'request<OntologyGraph>(`/api/v1/ontology/graph${suffix}`)' in api
    assert "export interface OntologyGraph" in types
    assert 'from "./data/kg_data.json"' not in app
    for interaction in ("kg-search-field", "kg-filter-chips", "kg-node-inspector"):
        assert interaction in app


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
    assert "2025历史数据 · 代理标签" in app
    assert "追问只读取当前运行记录" in app
    assert "不能修改概率、等级或 CAP" in app
    assert 'assistant: "决策简报"' in translations


def test_evidence_page_renders_relationship_network_and_node_inspector():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    styles = (FRONTEND / "src" / "styles.css").read_text(encoding="utf-8")
    for contract in ("observation-edge", "mechanism-edge", "citation-edge", "nodeInspector"):
        assert contract in app
    assert "network-canvas" in styles
    assert "graph-ring" not in app


def test_decision_brief_is_primary_and_follow_up_is_optional():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    for section in ("一句话结论", "主要依据", "交叉复核", "必须说明的限制", "optionalFollowup"):
        assert section in app


def test_visible_domain_vocabulary_is_localized_and_reports_follow_locale():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    translations = (FRONTEND / "src" / "i18n.ts").read_text(encoding="utf-8")
    for helper in (
        "riskLevelLabel",
        "consistencyLabel",
        "indicatorLabel",
        "mechanismLabel",
        "evidenceStatusLabel",
        "reportKindLabel",
    ):
        assert helper in app
        assert f"export const {helper}" in translations
    assert "report.language === locale" in app
    for leaked_literal in (
        "A / TASK CONTROL",
        "CURATED / AUDITED",
        "NO ACTIVE EXERCISE",
        "A / SAUDI GRID FIELD",
        "READING HISTORICAL FIELD",
        "B / DOCUMENT LIBRARY",
        "<span>NODE INSPECTOR</span>",
    ):
        assert leaked_literal not in app


def test_ui_ux_system_keeps_context_and_task_outputs_visible():
    app = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
    styles = (FRONTEND / "src" / "styles.css").read_text(encoding="utf-8")
    translations = (FRONTEND / "src" / "i18n.ts").read_text(encoding="utf-8")
    for component in ("active-run-chip", "analysis-summary", "network-selection-card", "artifact-grid"):
        assert component in app
    for token in ("--surface-raised", "--action", "--risk-high", "--focus"):
        assert token in styles
    assert "button:focus-visible" in styles
    assert "@media (max-width: 900px)" in styles
    assert 'analysisTitle: "事件诊断"' in translations
    assert 'reportsTitle: "提交材料"' in translations


def test_ui_design_system_documents_user_tasks_and_accessibility():
    design_system = (FRONTEND.parent / "docs" / "competition_app_design_system.md").read_text(encoding="utf-8")
    for contract in (
        "10–20 seconds",
        "current exercise",
        "`--focus`",
        "`focus-visible`",
        "390 px",
        "proxy-label",
    ):
        assert contract in design_system
