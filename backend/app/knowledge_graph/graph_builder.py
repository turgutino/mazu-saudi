"""Build a query-specific explanation view over the versioned knowledge base."""

from __future__ import annotations

from app.knowledge_graph.knowledge_base import literature, load_knowledge_base, mechanisms_for, sweet_mapping
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


def build_graph(prediction: PredictionResult) -> KnowledgeGraph:
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

    def add_edge(source: str, target: str, label: str, edge_type: str, step: int, semantics: str, rationale: str, confidence: float | None = None, evidence_ids: list[str] | None = None) -> None:
        nonlocal edge_seq
        edge_seq += 1
        edges.append(GraphEdge(
            id=f"e{edge_seq}", source=source, target=target, label=label,
            type=edge_type, step=step, semantics=semantics, confidence=confidence,
            rationale=rationale, evidence_ids=evidence_ids or [],
        ))

    case_id = f"case-{prediction.case_id}"
    pred_id = f"pred-{prediction.prediction_id}"
    model_id = f"model-{prediction.model_id}"
    hazard_id = f"hazard-{prediction.hazard}"
    region_id = f"region-{prediction.region_id}"
    risk_id = f"risk-{prediction.prediction_id}"
    warning_id = f"warning-{prediction.prediction_id}"

    add_node(id=case_id, label=f"ForecastCase\n{prediction.region_name}", type="case", group="anchor", step=0,
             evidence_kind="run", status="materialized", details={"initialTime": prediction.initial_time, "targetTime": prediction.target_time, "leadTimeHours": prediction.lead_time_hours})
    add_node(id=pred_id, label=f"Prediction\n{prediction.hazard_label}概率 {prediction.calibrated_probability:g}", type="prediction", group="anchor", step=1,
             evidence_kind="model", status="computed", details={"rawProbability": prediction.probability, "calibratedProbability": prediction.calibrated_probability, "uncertainty": prediction.uncertainty, "inputHash": prediction.input_hash})
    add_node(id=model_id, label=f"ModelVersion\n{prediction.model_name} {prediction.model_version}", type="model", group="input", step=1,
             evidence_kind="model", status="declared", details={"modelId": prediction.model_id, "version": prediction.model_version})
    add_node(id=hazard_id, label=f"HazardType\n{prediction.hazard_label}", type="hazard", group="input", step=1,
             evidence_kind="domain", status="controlled-vocabulary", details={"hazardId": prediction.hazard})
    add_node(id=region_id, label=f"SpatialUnit\n{prediction.region_name}", type="region", group="input", step=1,
             evidence_kind="observation", status="declared", details={"regionId": prediction.region_id})
    add_edge(case_id, pred_id, "PRODUCED", "PRODUCED", 1, "asserted", "该预测是此冻结预报案例的输出。")
    add_edge(model_id, pred_id, "GENERATED", "GENERATED", 1, "asserted", "预测结果声明了生成它的模型版本。")
    add_edge(pred_id, region_id, "FOR_REGION", "FOR_REGION", 1, "asserted", "预测空间范围。")
    add_edge(pred_id, hazard_id, "PREDICTS", "PREDICTS", 1, "asserted", "预测目标灾种。")

    feature_node_ids: dict[str, str] = {}
    for feature in prediction.features:
        fid = f"feat-{feature.feature}"
        feature_node_ids[feature.feature] = fid
        add_node(id=fid, label=f"{feature.feature_label}\n{feature.actual_value:g} {feature.unit}", type="feature", group="features", step=2,
                 navigate_tab="features", evidence_kind="model", status="computed-attribution", details={"indicator": feature.feature, "actualValue": feature.actual_value, "normalValue": feature.normal_value, "unit": feature.unit, "contribution": feature.contribution})
        add_edge(pred_id, fid, "HAS_ATTRIBUTION", "HAS_ATTRIBUTION", 2, "computed", "模型适配器返回的逐特征贡献；不是物理因果贡献。", confidence=None)

    for rule in prediction.rule_hits:
        if not rule.met:
            continue
        rid = f"rule-{rule.rule_id}"
        add_node(id=rid, label=f"PolicyRule\n{rule.rule_name}", type="rule", group="rules", step=3,
                 navigate_tab="rules", evidence_kind="policy", status="triggered", details={"condition": rule.condition, "actualValue": rule.actual_value, "threshold": rule.threshold, "weight": rule.weight})
        add_edge(rid, risk_id, "INFORMS", "INFORMS", 5, "derived", "命中的版本化政策规则参与风险等级映射。")
        indicator_key = _indicator_key_from_condition(rule.condition)
        if indicator_key and indicator_key in feature_node_ids:
            add_edge(feature_node_ids[indicator_key], rid, "USES", "USES", 3, "asserted", "规则条件直接引用该指标。")

    mechanism_config = {item["id"]: item for item in mechanisms_for(prediction.hazard, prediction.region_id)}
    for mechanism in prediction.mechanisms:
        config = mechanism_config[mechanism.path_id]
        mid = f"mech-{mechanism.path_id}"
        add_node(id=mid, label=f"MechanismCompatibility\n{mechanism.path_name}", type="mechanism", group="mechanisms", step=4,
                 navigate_tab="mechanisms", evidence_kind="domain", status="compatible" if mechanism.support_score >= 0.42 else "weak-or-contrary", details={"supportScore": mechanism.support_score, "confidence": mechanism.confidence, "summary": mechanism.summary})
        for signal in config["signals"]:
            fid = feature_node_ids.get(signal["indicator"])
            if fid:
                add_edge(fid, mid, "CONSISTENT_WITH", "CONSISTENT_WITH", 4, "derived", f"该指标按知识包中的角色与机制相容；权重 {signal['weight']:.0%}。", confidence=mechanism.support_score, evidence_ids=mechanism.evidence_ids)
        add_edge(mid, hazard_id, "FAVOURS", "FAVOURS", 4, "asserted", "该机制描述有利环境，不断言灾害必然发生。", confidence=mechanism.support_score, evidence_ids=mechanism.evidence_ids)

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

    return KnowledgeGraph(
        prediction_id=prediction.prediction_id,
        graph_version=catalog["version"],
        generated_at=prediction.created_at,
        disclaimer=catalog["semantics"]["disclaimer"],
        nodes=nodes,
        edges=edges,
    )
