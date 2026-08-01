"""Build a query-specific explanation view over the versioned knowledge base."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.data.indicator_provider import INDICATOR_SPECS
from app.domain.forecast_data import ForecastDataSnapshot
from app.knowledge_graph.indicator_semantics import (
    canonical_indicator_key,
    indicator_aggregation,
    indicator_ontology_details,
    indicator_role,
)
from app.knowledge_graph.knowledge_base import (
    literature,
    load_knowledge_base,
    mechanisms_for,
    ontology_metadata,
    sweet_mapping,
)
from app.schemas.graph import GraphEdge, GraphNode, KnowledgeGraph
from app.schemas.prediction import PredictionResult


_RISK_TO_WARNING_LABEL = {
    "green": None,
    "yellow": "黄色预警",
    "orange": "橙色预警",
    "red": "红色预警",
}


def _indicator_key_from_condition(condition: str) -> str | None:
    token = condition.split(" ", 1)[0]
    return None if token in ("calibrated_probability", "region_sensitivity") else token


def build_graph(
    prediction: PredictionResult,
    forecast_snapshot: ForecastDataSnapshot | None = None,
) -> KnowledgeGraph:
    catalog = load_knowledge_base()
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    node_ids: set[str] = set()
    edge_seq = 0

    def add_node(**kwargs) -> None:
        node = GraphNode(**kwargs)
        if node.id not in node_ids:
            nodes.append(node)
            node_ids.add(node.id)

    def add_edge(source: str, target: str, label: str, edge_type: str, step: int, semantics: str, rationale: str, confidence: float | None = None, evidence_ids: list[str] | None = None, details: dict[str, str | float | bool | None] | None = None) -> None:
        nonlocal edge_seq
        edge_seq += 1
        edges.append(GraphEdge(
            id=f"e{edge_seq}", source=source, target=target, label=label,
            type=edge_type, step=step, semantics=semantics, confidence=confidence,
            rationale=rationale, evidence_ids=evidence_ids or [], details=details or {},
        ))

    case_id = f"case-{prediction.case_id}"
    pred_id = f"pred-{prediction.prediction_id}"
    model_id = f"model-{prediction.model_id}"
    hazard_id = f"hazard-{prediction.hazard}"
    region_id = f"region-{prediction.region_id}"
    risk_id = f"risk-{prediction.prediction_id}"
    warning_id = f"warning-{prediction.prediction_id}"
    snapshot_external_id = (
        forecast_snapshot.snapshot_id
        if forecast_snapshot is not None
        else prediction.forecast_snapshot_id
        or f"archive-{prediction.input_hash[:16]}"
    )
    snapshot_id = f"snapshot-{snapshot_external_id}"

    add_node(id=case_id, label=f"ForecastCase\n{prediction.region_name}", type="case", group="anchor", step=0,
             evidence_kind="run", status="materialized", details={"initialTime": prediction.initial_time, "targetTime": prediction.target_time, "leadTimeHours": prediction.lead_time_hours})
    add_node(id=pred_id, label=f"Prediction\n{prediction.hazard_label}概率 {prediction.calibrated_probability:g}", type="prediction", group="anchor", step=1,
             evidence_kind="model", status="computed", details={"rawProbability": prediction.probability, "calibratedProbability": prediction.calibrated_probability, "uncertainty": prediction.uncertainty, "inputHash": prediction.input_hash, "attributionMethod": prediction.attribution_method, "attributionOutput": prediction.attribution_output, "attributionBaseValue": prediction.attribution_base_value, "attributionModelOutput": prediction.attribution_model_output})
    add_node(id=model_id, label=f"ModelVersion\n{prediction.model_name} {prediction.model_version}", type="model", group="input", step=1,
             evidence_kind="model", status="declared", details={"modelId": prediction.model_id, "version": prediction.model_version})
    add_node(id=hazard_id, label=f"HazardType\n{prediction.hazard_label}", type="hazard", group="input", step=1,
             evidence_kind="domain", status="controlled-vocabulary", details={"hazardId": prediction.hazard})
    add_node(id=region_id, label=f"SpatialUnit\n{prediction.region_name}", type="region", group="input", step=1,
             evidence_kind="observation", status="declared", details={"regionId": prediction.region_id})
    target_time = datetime.fromisoformat(prediction.target_time.replace("Z", "+00:00"))
    default_valid_from = (target_time - timedelta(hours=24)).isoformat()
    snapshot_source = (
        forecast_snapshot.source if forecast_snapshot is not None else prediction.forecast_source
    ) or "era5-archive"
    snapshot_kind = "third-party-forecast" if prediction.data_tier == "tier2_live" else "historical-indicator-archive"
    snapshot_details = {
        "snapshotId": snapshot_external_id,
        "snapshotKind": snapshot_kind,
        "source": snapshot_source,
        "dataTier": prediction.data_tier,
        "fetchedAt": forecast_snapshot.fetched_at if forecast_snapshot is not None else None,
        "validFrom": forecast_snapshot.valid_from if forecast_snapshot is not None else default_valid_from,
        "validTo": forecast_snapshot.valid_to if forecast_snapshot is not None else prediction.target_time,
        "featureVersion": forecast_snapshot.feature_version if forecast_snapshot is not None else "historical-daily-v1",
        "status": forecast_snapshot.status if forecast_snapshot is not None else "materialized-with-prediction",
        "validationError": forecast_snapshot.validation_error if forecast_snapshot is not None else None,
        "inputHash": prediction.input_hash,
    }
    add_node(
        id=snapshot_id,
        label=f"InputSnapshot\n{snapshot_source}",
        type="snapshot",
        group="input",
        step=1,
        evidence_kind="forecast" if prediction.data_tier == "tier2_live" else "observation",
        status=str(snapshot_details["status"]),
        details=snapshot_details,
    )
    add_edge(case_id, pred_id, "PRODUCED", "PRODUCED", 1, "asserted", "该预测是此冻结预报案例的输出。")
    add_edge(case_id, snapshot_id, "USES_INPUT", "USES_INPUT", 1, "asserted", "该冻结案例声明本次模型运行使用的不可变输入快照。")
    add_edge(model_id, pred_id, "GENERATED", "GENERATED", 1, "asserted", "预测结果声明了生成它的模型版本。")
    add_edge(pred_id, region_id, "FOR_REGION", "FOR_REGION", 1, "asserted", "预测空间范围。")
    add_edge(pred_id, hazard_id, "PREDICTS", "PREDICTS", 1, "asserted", "预测目标灾种。")

    indicator_node_ids: dict[str, str] = {}
    verified_tree_shap = prediction.attribution_method == "tree_shap"
    attribution_rationale = (
        "Tree SHAP在模型raw log-odds尺度上的局部归因；正值提高事件倾向、负值降低事件倾向，不表示物理因果。"
        if verified_tree_shap
        else "该旧记录未声明可验证的归因方法，不应解读为SHAP贡献或物理因果。"
    )
    raw_by_canonical: dict[str, tuple[str, float | None]] = {}
    for raw_key, value in prediction.raw_indicators.items():
        canonical = canonical_indicator_key(raw_key)
        if canonical not in raw_by_canonical or raw_key == canonical:
            raw_by_canonical[canonical] = (raw_key, value)

    feature_by_canonical = {
        canonical_indicator_key(feature.feature): feature
        for feature in prediction.features
    }
    verified_indicator_provenance = (
        prediction.indicator_provenance_version == "real-inputs-v1"
        or prediction.data_tier == "tier2_live"
    )
    mechanism_config = {item["id"]: item for item in mechanisms_for(prediction.hazard, prediction.region_id)}
    mechanism_signal_keys = {
        canonical_indicator_key(signal["indicator"])
        for item in mechanism_config.values()
        for signal in item["signals"]
    }
    rule_indicator_keys = {
        canonical_indicator_key(key)
        for rule in prediction.rule_hits
        if (key := _indicator_key_from_condition(rule.condition)) is not None
    }
    trusted_mechanism_keys = (
        mechanism_signal_keys
        if verified_indicator_provenance
        else mechanism_signal_keys & set(feature_by_canonical)
    )
    relevant_keys = set(feature_by_canonical) | trusted_mechanism_keys | rule_indicator_keys

    for canonical in sorted(relevant_keys):
        raw_entry = raw_by_canonical.get(canonical)
        feature = feature_by_canonical.get(canonical)
        if raw_entry is None and feature is None:
            continue
        raw_key, raw_value = raw_entry if raw_entry is not None else (canonical, feature.actual_value)
        spec = INDICATOR_SPECS.get(raw_key) or INDICATOR_SPECS.get(
            {"daily_precip_total": "daily_precip", "pwat": "pw", "t2m_c": "t2m", "wind10_speed": "wind_10m"}.get(canonical, canonical)
        )
        label = feature.feature_label if feature is not None else spec.label if spec is not None else canonical
        unit = feature.unit if feature is not None else spec.unit if spec is not None else ""
        actual_label = "缺测" if raw_value is None else f"{raw_value:g} {unit}".strip()
        iid = f"indicator-{canonical}"
        indicator_node_ids[canonical] = iid
        add_node(
            id=iid,
            label=f"{label}\n{actual_label}",
            type="indicator",
            group="features",
            step=2,
            navigate_tab="features" if feature is not None else "mechanisms",
            evidence_kind="forecast" if prediction.data_tier == "tier2_live" else "observation",
            status="missing" if raw_value is None else "available",
            details={
                "indicator": canonical,
                "sourceField": raw_key,
                "actualValue": raw_value,
                "unit": unit,
                "source": snapshot_source,
                "snapshotId": snapshot_external_id,
                "aggregation": indicator_aggregation(canonical, prediction.data_tier),
                "indicatorRole": indicator_role(canonical),
                "isModelFeature": feature is not None,
                **indicator_ontology_details(canonical),
            },
        )
        add_edge(snapshot_id, iid, "PROVIDES", "PROVIDES", 2, "asserted", "输入快照保存该指标值、来源和时间窗口。")
        if feature is not None:
            add_edge(iid, model_id, "USED_BY", "USED_BY", 2, "asserted", "该指标值是本次模型运行实际使用的输入特征。")
            add_edge(
                pred_id,
                iid,
                "HAS_ATTRIBUTION",
                "HAS_ATTRIBUTION",
                2,
                "computed" if verified_tree_shap else "asserted",
                f"{attribution_rationale} 本特征贡献 {feature.contribution:+g}。",
                details={
                    "contribution": feature.contribution,
                    "method": prediction.attribution_method,
                    "outputScale": prediction.attribution_output,
                    "normalValue": feature.normal_value,
                },
            )

    for rule in prediction.rule_hits:
        if not rule.met:
            continue
        rid = f"rule-{rule.rule_id}"
        add_node(id=rid, label=f"PolicyRule\n{rule.rule_name}", type="rule", group="rules", step=3,
                 navigate_tab="rules", evidence_kind="policy", status="triggered", details={"condition": rule.condition, "actualValue": rule.actual_value, "threshold": rule.threshold, "weight": rule.weight})
        add_edge(rid, risk_id, "INFORMS", "INFORMS", 5, "derived", "命中的版本化政策规则参与风险等级映射。")
        indicator_key = _indicator_key_from_condition(rule.condition)
        canonical_key = canonical_indicator_key(indicator_key) if indicator_key else None
        if canonical_key and canonical_key in indicator_node_ids:
            add_edge(indicator_node_ids[canonical_key], rid, "USES", "USES", 3, "asserted", "规则条件直接引用该指标值。")

    for mechanism in prediction.mechanisms:
        config = mechanism_config[mechanism.path_id]
        mid = f"mech-{mechanism.path_id}"
        add_node(id=mid, label=f"MechanismCompatibility\n{mechanism.path_name}", type="mechanism", group="mechanisms", step=4,
                 navigate_tab="mechanisms", evidence_kind="domain", status=("compatible" if mechanism.support_score >= 0.42 else "weak-or-contrary") if verified_indicator_provenance else "legacy-unverified-inputs", details={"supportScore": mechanism.support_score if verified_indicator_provenance else None, "confidence": mechanism.confidence if verified_indicator_provenance else None, "summary": mechanism.summary, "indicatorProvenanceVersion": prediction.indicator_provenance_version, "inputWarning": None if verified_indicator_provenance else "旧历史记录含未验证的解释指标，已隐藏机制得分和相容边。"})
        for signal in config["signals"]:
            if not verified_indicator_provenance:
                continue
            iid = indicator_node_ids.get(canonical_indicator_key(signal["indicator"]))
            if iid:
                add_edge(iid, mid, "CONSISTENT_WITH", "CONSISTENT_WITH", 4, "derived", f"该指标值按知识包中的方向和权重与机制相容；权重 {signal['weight']:.0%}，不表示模型归因或物理因果。", confidence=mechanism.support_score, evidence_ids=mechanism.evidence_ids)
        add_edge(
            mid,
            hazard_id,
            "FAVOURS",
            "FAVOURS",
            4,
            "asserted",
            "该机制描述有利环境，不断言灾害必然发生。"
            if verified_indicator_provenance
            else "该机制的一般领域关系仍保留，但旧记录的个例相容度不可验证。",
            confidence=mechanism.support_score if verified_indicator_provenance else None,
            evidence_ids=mechanism.evidence_ids,
        )

        for evidence_id in mechanism.evidence_ids:
            source = literature(evidence_id)
            sid = f"source-{evidence_id}"
            add_node(id=sid, label=f"Literature\n{source['title']}", type="source", group="sources", step=4,
                     evidence_kind="literature", status="catalogued-not-case-proof", details={"sourceId": evidence_id, "year": source["year"], "doi": source.get("doi"), "url": source["landing_url"]})
            add_edge(mid, sid, "GROUNDED_IN", "GROUNDED_IN", 4, "asserted", "文献支持机制的一般适用性，不证明本次个例因果。", evidence_ids=[evidence_id])

        for concept in config.get("sweetConcepts", []):
            mapping = sweet_mapping(concept)
            if not mapping:
                continue
            oid = f"sweet-{concept}"
            add_node(id=oid, label=f"SWEET\n{concept}", type="ontology", group="sources", step=4,
                     evidence_kind="ontology", status=mapping["relation"], details={"targetIri": mapping["target_iri"], "mapping": mapping["relation"], "rationale": mapping["rationale"]})
            add_edge(mid, oid, "ALIGNED_WITH", "ALIGNED_WITH", 4, "asserted", mapping["rationale"])

    add_node(id=risk_id, label=f"RiskAssessment\n{prediction.risk_label}", type="risk", group="anchor", step=5,
             evidence_kind="decision", status="computed", details={"level": prediction.risk_level, "description": prediction.risk_description})
    add_edge(pred_id, risk_id, "ASSESSED_AS", "ASSESSED_AS", 5, "derived", "风险评估由概率、区域敏感性和政策规则组合得到；不等同于模型概率。")

    for event in prediction.similar_events:
        eid = f"event-{event.event_id}"
        add_node(id=eid, label=f"AnalogCase\n{event.date} {event.region}", type="event", group="events", step=6,
                 navigate_tab="history", evidence_kind="case", status=event.verification_status, details={"similarity": event.similarity, "dataCoverage": event.data_coverage, "source": event.source_title, "description": event.description})
        rationale = "；".join(f"{item.label} {item.score:.0%}（{item.explanation}）" for item in event.similarity_dimensions)
        add_edge(pred_id, eid, "SIMILAR_TO", "SIMILAR_TO", 6, "computed", rationale, confidence=event.similarity)

    warning_label = _RISK_TO_WARNING_LABEL[prediction.risk_level]
    if warning_label:
        add_node(id=warning_id, label=f"WarningProduct\n{prediction.hazard_label}{warning_label}", type="warning", group="anchor", step=6,
                 evidence_kind="decision", status="candidate", details={"level": prediction.risk_level})
        add_edge(risk_id, warning_id, "RESULTS_IN", "RESULTS_IN", 6, "derived", "依据当前业务政策映射为候选预警产品。")

    ontology = ontology_metadata()
    return KnowledgeGraph(
        prediction_id=prediction.prediction_id,
        graph_version=catalog["version"],
        ontology_id=ontology["id"],
        ontology_version=ontology["version"],
        generated_at=prediction.created_at,
        disclaimer=catalog["semantics"]["disclaimer"],
        nodes=nodes,
        edges=edges,
    )
