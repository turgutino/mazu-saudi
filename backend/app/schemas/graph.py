from __future__ import annotations

from typing import Literal

from .common import CamelModel

NodeType = Literal[
    "case",
    "prediction",
    "model",
    "hazard",
    "region",
    "feature",
    "rule",
    "mechanism",
    "risk",
    "event",
    "warning",
    "source",
    "ontology",
    "snapshot",
    "indicator",
]
NodeGroupKey = Literal["anchor", "input", "features", "rules", "mechanisms", "events", "sources"]
EdgeType = Literal[
    "PRODUCED",
    "USES",
    "TRIGGERS",
    "CONSISTENT_WITH",
    "FAVOURS",
    "GROUNDED_IN",
    "ALIGNED_WITH",
    "INFORMS",
    "ASSESSED_AS",
    "SIMILAR_TO",
    "RESULTS_IN",
    "PREDICTS",
    "HAS_ATTRIBUTION",
    "INSTANCE_OF",
    "FOR_REGION",
    "GENERATED",
    "USES_INPUT",
    "PROVIDES",
    "USED_BY",
]


class GraphNode(CamelModel):
    id: str
    label: str
    type: NodeType
    group: NodeGroupKey
    step: int
    navigate_tab: str | None = None
    navigate_node_id: str | None = None
    evidence_kind: Literal["run", "model", "forecast", "observation", "policy", "domain", "literature", "case", "decision", "ontology"]
    status: str
    details: dict[str, str | float | bool | None]
    x: float | None = None
    y: float | None = None
    fx: float | None = None
    fy: float | None = None


class GraphEdge(CamelModel):
    id: str
    source: str
    target: str
    label: str
    type: EdgeType
    step: int
    semantics: Literal["asserted", "derived", "computed"]
    confidence: float | None = None
    rationale: str
    evidence_ids: list[str] = []
    details: dict[str, str | float | bool | None] = {}


class KnowledgeGraph(CamelModel):
    prediction_id: str
    graph_version: str
    ontology_id: str
    ontology_version: str
    generated_at: str
    disclaimer: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
