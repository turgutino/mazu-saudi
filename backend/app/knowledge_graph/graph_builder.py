"""Build a single prediction's local explanation graph (初步设计.md 第5节).

v1 scope: only the "local explanation graph" for one PredictionResult, laid
out along the same 7-step timeline as frontend/src/mocks/graphData.ts
(TIMELINE_STEPS 0-6: case -> prediction -> features -> rules -> mechanisms ->
risk -> events/warning). No global statistical knowledge graph is built or
persisted here — see backend/app/knowledge_graph/store.py (not yet
implemented; TODO for a future ontology redesign).
"""

from __future__ import annotations

from app.schemas.graph import GraphEdge, GraphNode, KnowledgeGraph
from app.schemas.prediction import PredictionResult

_RISK_TO_WARNING_LABEL = {
    "green": None,
    "yellow": "黄色预警",
    "orange": "橙色预警",
    "red": "红色预警",
}


def _indicator_key_from_condition(condition: str) -> str | None:
    """Extract the leading indicator key from a policy-generated condition string.

    Indicator rule conditions look like "cape >= 2000"; probability/sensitivity
    rule conditions look like "calibrated_probability >= 0.7" or
    "region_sensitivity == high" and are not tied to a single feature.
    """

    token = condition.split(" ", 1)[0]
    if token in ("calibrated_probability", "region_sensitivity"):
        return None
    return token


def build_graph(prediction: PredictionResult) -> KnowledgeGraph:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    edge_seq = 0

    def next_edge_id() -> str:
        nonlocal edge_seq
        edge_seq += 1
        return f"e{edge_seq}"

    case_id = f"case-{prediction.case_id}"
    pred_id = f"pred-{prediction.prediction_id}"
    model_id = f"model-{prediction.model_id}"
    hazard_id = f"hazard-{prediction.hazard}"
    region_id = f"region-{prediction.region_id}"
    risk_id = f"risk-{prediction.prediction_id}"
    warning_id = f"warning-{prediction.prediction_id}"

    # step 0: case
    nodes.append(GraphNode(id=case_id, label=f"ForecastCase\n{prediction.region_name}", type="case", group="anchor", step=0))

    # step 1: prediction + input context
    nodes.append(GraphNode(id=pred_id, label=f"Prediction\n{prediction.hazard_label}概率 {prediction.calibrated_probability:g}", type="prediction", group="anchor", step=1))
    nodes.append(GraphNode(id=model_id, label=f"ModelVersion\n{prediction.model_name} {prediction.model_version}", type="model", group="input", step=1))
    nodes.append(GraphNode(id=hazard_id, label=f"HazardType\n{prediction.hazard_label}", type="hazard", group="input", step=1))
    nodes.append(GraphNode(id=region_id, label=f"Region\n{prediction.region_name}", type="region", group="input", step=1))

    edges.append(GraphEdge(id=next_edge_id(), source=case_id, target=pred_id, label="PRODUCED", type="PRODUCED", step=1))
    edges.append(GraphEdge(id=next_edge_id(), source=model_id, target=pred_id, label="GENERATED", type="GENERATED", step=1))
    edges.append(GraphEdge(id=next_edge_id(), source=pred_id, target=region_id, label="FOR_REGION", type="FOR_REGION", step=1))
    edges.append(GraphEdge(id=next_edge_id(), source=pred_id, target=hazard_id, label="PREDICTS", type="PREDICTS", step=1))

    # step 2: feature attributions
    feature_node_ids: dict[str, str] = {}
    for feature in prediction.features:
        fid = f"feat-{feature.feature}"
        feature_node_ids[feature.feature] = fid
        nodes.append(GraphNode(id=fid, label=f"{feature.feature_label}\n{feature.actual_value:g} {feature.unit}", type="feature", group="features", step=2, navigate_tab="features"))
        edges.append(GraphEdge(id=next_edge_id(), source=pred_id, target=fid, label="HAS_ATTRIBUTION", type="HAS_ATTRIBUTION", step=2))

    # step 3: triggered rules
    rule_node_ids: list[str] = []
    for rule in prediction.rule_hits:
        if not rule.met:
            continue
        rid = f"rule-{rule.rule_id}"
        rule_node_ids.append(rid)
        nodes.append(GraphNode(id=rid, label=f"Rule\n{rule.rule_name}", type="rule", group="rules", step=3, navigate_tab="rules"))
        edges.append(GraphEdge(id=next_edge_id(), source=pred_id, target=rid, label="TRIGGERS", type="TRIGGERS", step=3))
        indicator_key = _indicator_key_from_condition(rule.condition)
        if indicator_key and indicator_key in feature_node_ids:
            edges.append(GraphEdge(id=next_edge_id(), source=feature_node_ids[indicator_key], target=rid, label="USES", type="USES", step=3))

    # step 4: physical mechanisms
    mech_node_ids: list[str] = []
    for mechanism in prediction.mechanisms:
        mid = f"mech-{mechanism.path_id}"
        mech_node_ids.append(mid)
        nodes.append(GraphNode(id=mid, label=f"Mechanism\n{mechanism.path_name}", type="mechanism", group="mechanisms", step=4, navigate_tab="mechanisms"))
    if mech_node_ids:
        for i, rid in enumerate(rule_node_ids):
            target = mech_node_ids[0] if i % 2 == 0 else mech_node_ids[-1]
            edges.append(GraphEdge(id=next_edge_id(), source=rid, target=target, label="SUPPORTED_BY", type="SUPPORTED_BY", step=4))

    # step 5: risk assessment
    nodes.append(GraphNode(id=risk_id, label=f"RiskAssessment\n{prediction.risk_label}", type="risk", group="anchor", step=5))
    edges.append(GraphEdge(id=next_edge_id(), source=pred_id, target=risk_id, label="ASSESSED_AS", type="ASSESSED_AS", step=5))

    # step 6: similar historical events + warning
    for event in prediction.similar_events:
        eid = f"event-{event.event_id}"
        nodes.append(GraphNode(id=eid, label=f"HistoricalEvent\n{event.date} {event.region}{event.hazard}", type="event", group="events", step=6, navigate_tab="history"))
        edges.append(GraphEdge(id=next_edge_id(), source=risk_id, target=eid, label="SIMILAR_TO", type="SIMILAR_TO", step=6))

    warning_label = _RISK_TO_WARNING_LABEL[prediction.risk_level]
    if warning_label:
        nodes.append(GraphNode(id=warning_id, label=f"Warning\n{prediction.hazard_label}{warning_label}", type="warning", group="anchor", step=6))
        edges.append(GraphEdge(id=next_edge_id(), source=risk_id, target=warning_id, label="RESULTS_IN", type="RESULTS_IN", step=6))

    return KnowledgeGraph(prediction_id=prediction.prediction_id, nodes=nodes, edges=edges)
