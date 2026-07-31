"""Executable semantic gates for the MAZU explanation evidence profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


MAZU = "urn:mazu-saudi:ontology:"
CONCEPT = "urn:mazu-saudi:concept:"
PROV_WAS_GENERATED_BY = "http://www.w3.org/ns/prov#wasGeneratedBy"


@dataclass(frozen=True)
class OntologySemanticSummary:
    version: str
    resource_count: int
    threshold_state_count: int
    hazard_screening_state_count: int
    cf_property_count: int


@dataclass(frozen=True)
class GraphSemanticSummary:
    state_instance_count: int
    assertion_count: int
    edge_count: int


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _expand(value: str, context: dict[str, Any]) -> str:
    if value.startswith(("http://", "https://", "urn:")):
        return value
    if ":" in value:
        prefix, local = value.split(":", 1)
        namespace = context.get(prefix)
        if isinstance(namespace, str):
            return f"{namespace}{local}"
    vocabulary = context.get("@vocab")
    return f"{vocabulary}{value}" if isinstance(vocabulary, str) else value


def validate_ontology_semantics(
    payload: dict[str, Any],
) -> OntologySemanticSummary:
    """Reject structurally valid JSON-LD that violates the local domain model."""

    context = payload.get("@context")
    graph = payload.get("@graph")
    if not isinstance(context, dict) or not isinstance(graph, list):
        raise ValueError("Ontology semantic validation requires @context and @graph")
    resources = {
        _expand(node["@id"], context): node
        for node in graph
        if isinstance(node, dict) and isinstance(node.get("@id"), str)
    }

    def resource(local_name: str) -> dict[str, Any]:
        iri = f"{MAZU}{local_name}"
        if iri not in resources:
            raise ValueError(f"Ontology semantic resource is missing: {iri}")
        return resources[iri]

    expected_parents = {
        "ThresholdDerivedState": f"{MAZU}AtmosphericState",
        "IndicatorState": f"{MAZU}ThresholdDerivedState",
        "ExtremeWeatherState": f"{MAZU}IndicatorState",
        "TemporalContext": f"{MAZU}EvidenceContext",
        "SeasonalContext": f"{MAZU}TemporalContext",
        "DataAvailabilityContext": f"{MAZU}EvidenceContext",
    }
    for local_name, expected_parent in expected_parents.items():
        parents = {
            _expand(value, context)
            for value in _as_list(resource(local_name).get("subClassOf"))
        }
        if expected_parent not in parents:
            raise ValueError(
                f"{MAZU}{local_name} must inherit from {expected_parent}"
            )

    expected_ranges = {
        "derivedFromIndicator": f"{MAZU}DerivedIndicator",
        "screenedByState": f"{MAZU}AtmosphericState",
        "applicableUnder": f"{MAZU}EvidenceContext",
    }
    for local_name, expected_range in expected_ranges.items():
        actual = _expand(str(resource(local_name).get("range", "")), context)
        if actual != expected_range:
            raise ValueError(
                f"{MAZU}{local_name} range must be {expected_range}"
            )

    threshold_types = {
        f"{MAZU}IndicatorState",
        f"{MAZU}ExtremeWeatherState",
    }
    threshold_states = []
    hazard_states = []
    for iri, node in resources.items():
        node_type = _expand(str(node.get("@type", "")), context)
        if node_type in threshold_types:
            threshold_states.append(iri)
            indicators = _as_list(node.get("derivedFromIndicator"))
            if not indicators or not node.get("thresholdDefinition"):
                raise ValueError(
                    f"Threshold-derived concept lacks indicator or threshold: {iri}"
                )
            for indicator in indicators:
                indicator_iri = _expand(str(indicator), context)
                indicator_node = resources.get(indicator_iri)
                if indicator_node is None or _expand(
                    str(indicator_node.get("@type", "")),
                    context,
                ) != f"{MAZU}DerivedIndicator":
                    raise ValueError(
                        f"Threshold state references invalid indicator: {indicator_iri}"
                    )
        elif node_type == f"{MAZU}HazardFavourableState":
            hazard_states.append(iri)
            screening_states = _as_list(node.get("screenedByState"))
            if not screening_states:
                raise ValueError(f"Hazard screening state lacks support state: {iri}")
            for screening_state in screening_states:
                screening_iri = _expand(str(screening_state), context)
                if screening_iri not in resources:
                    raise ValueError(
                        f"Hazard screening state references unknown state: {screening_iri}"
                    )

    cf_properties = (
        "cfStandardName",
        "cfCellMethods",
        "cfCoordinateConstraint",
        "cfSupportingStandardName",
    )
    for local_name in cf_properties:
        node = resource(local_name)
        if node.get("@type") != "owl:DatatypeProperty":
            raise ValueError(f"{MAZU}{local_name} must be an OWL datatype property")
        if node.get("domain") != "mazu:DerivedIndicator":
            raise ValueError(f"{MAZU}{local_name} must target DerivedIndicator")

    boundary = str(payload.get("claimBoundary", ""))
    if "ineligible for causal explanation" not in boundary:
        raise ValueError("Ontology claim boundary must prohibit causal eligibility")

    return OntologySemanticSummary(
        version=str(payload.get("versionInfo", "")),
        resource_count=len(resources) + 1,
        threshold_state_count=len(threshold_states),
        hazard_screening_state_count=len(hazard_states),
        cf_property_count=len(cf_properties),
    )


def validate_graph_semantics(
    nodes: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
    evidence: Iterable[dict[str, Any]],
) -> GraphSemanticSummary:
    """Reject graph records that break provenance or non-causal state contracts."""

    node_rows = list(nodes)
    edge_rows = list(edges)
    evidence_rows = list(evidence)
    outgoing: dict[str, dict[str, list[str]]] = {}
    for edge in edge_rows:
        outgoing.setdefault(edge["source_id"], {}).setdefault(
            edge["predicate_iri"],
            [],
        ).append(edge["target_id"])

    state_classes = {
        f"{MAZU}IndicatorState",
        f"{MAZU}ExtremeWeatherState",
    }
    state_instances = [
        node for node in node_rows if node["ontology_class_iri"] in state_classes
    ]
    for node in state_instances:
        if not outgoing.get(node["node_id"], {}).get(
            f"{MAZU}derivedFromIndicator"
        ):
            raise ValueError(
                f"State instance lacks derivedFromIndicator: {node['node_id']}"
            )

    assertions = [
        node
        for node in node_rows
        if node["ontology_class_iri"] == f"{MAZU}LaggedAssociationAssertion"
    ]
    required_predicates = {
        f"{MAZU}sourceState",
        f"{MAZU}targetState",
        f"{MAZU}applicableUnder",
        PROV_WAS_GENERATED_BY,
    }
    for assertion in assertions:
        assertion_edges = outgoing.get(assertion["node_id"], {})
        missing = sorted(required_predicates - set(assertion_edges))
        if missing:
            raise ValueError(
                f"Evidence assertion lacks required edges: "
                f"{assertion['node_id']} missing={missing}"
            )
        properties = assertion.get("properties", {})
        if not properties.get("evidence_class"):
            raise ValueError(
                f"Evidence assertion lacks evidence class: {assertion['node_id']}"
            )
        if properties.get("eligible_for_causal_explanation") is not False:
            raise ValueError(
                f"Evidence assertion is causally eligible: {assertion['node_id']}"
            )

    if any(row.get("eligible_for_causal_explanation") not in (0, False) for row in evidence_rows):
        raise ValueError("Evidence table contains a causally eligible assertion")

    return GraphSemanticSummary(
        state_instance_count=len(state_instances),
        assertion_count=len(assertions),
        edge_count=len(edge_rows),
    )
