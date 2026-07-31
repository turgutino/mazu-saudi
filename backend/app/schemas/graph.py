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
]
NodeGroupKey = Literal["anchor", "input", "features", "rules", "mechanisms", "events"]
EdgeType = Literal[
    "PRODUCED",
    "USES",
    "TRIGGERS",
    "SUPPORTED_BY",
    "ASSESSED_AS",
    "SIMILAR_TO",
    "RESULTS_IN",
    "PREDICTS",
    "HAS_ATTRIBUTION",
    "INSTANCE_OF",
    "FOR_REGION",
    "GENERATED",
]


class GraphNode(CamelModel):
    id: str
    label: str
    type: NodeType
    group: NodeGroupKey
    step: int
    navigate_tab: str | None = None
    navigate_node_id: str | None = None
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


class KnowledgeGraph(CamelModel):
    prediction_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
