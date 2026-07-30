"""Versioned weather ontology and local SQLite materialization."""

from .alignment import AlignmentSummary, validate_alignment_manifest
from .store import OntologyStore, materialize_ontology

__all__ = [
    "AlignmentSummary",
    "OntologyStore",
    "materialize_ontology",
    "validate_alignment_manifest",
]
