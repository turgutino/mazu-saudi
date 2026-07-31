"""Statistical knowledge-graph extraction over versioned indicator cubes."""

from .builder import (
    BuildConfig,
    BuildResult,
    DEFAULT_STATE_SPECS,
    IndicatorStateSpec,
    build_statistical_knowledge_graph,
)
from .store import KnowledgeGraphStore
from .literature import LiteratureEvidenceStore
from .external_background import (
    BackgroundRunResult,
    KWGBackgroundStore,
    run_kwg_enrichment,
    validate_kwg_snapshot,
)
from .explanation import HazardExplanationQuery
from .rebuild import REBUILD_CONTRACT_VERSION, rebuild_explanation_graph

__all__ = [
    "BuildConfig",
    "BuildResult",
    "BackgroundRunResult",
    "DEFAULT_STATE_SPECS",
    "IndicatorStateSpec",
    "KnowledgeGraphStore",
    "HazardExplanationQuery",
    "KWGBackgroundStore",
    "LiteratureEvidenceStore",
    "REBUILD_CONTRACT_VERSION",
    "build_statistical_knowledge_graph",
    "rebuild_explanation_graph",
    "run_kwg_enrichment",
    "validate_kwg_snapshot",
]
