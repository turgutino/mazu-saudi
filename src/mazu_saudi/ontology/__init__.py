"""Versioned weather ontology and local SQLite materialization."""

from .store import OntologyStore, materialize_ontology

__all__ = ["OntologyStore", "materialize_ontology"]
