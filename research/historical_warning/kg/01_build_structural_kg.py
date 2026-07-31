# =============================================================================
# MAZU Saudi Arabia — Hazard Mechanism & Evidence Graph (API-free)
#
# Builds an auditable multi-relation evidence graph from:
#   1. Indicator metadata      (formula, unit, meaning, data source)
#   2. Hazard detection logic   (flash_flood_risk formula -> contributes_to)
#   3. Hand-authored domain assertions (explicitly labelled as such)
#   4. 2025 dataset extrema     (samples, not independently verified events)
#
# Pairwise correlations are written to a separate observational-analysis
# artifact. They are deliberately excluded from the evidence graph because
# association, shared seasonality, and formula ancestry do not establish
# mechanism or causality.
#
# Outputs:
#   kg/kg_data.json                       evidence graph
#   kg/kg_observational_associations.json isolated Pearson associations
# =============================================================================

import os
import json
import itertools
import numpy as np
import xarray as xr
import networkx as nx
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(
    os.environ.get("MAZU_HISTORICAL_DATA_DIR", os.path.join(HERE, "..", "data")),
    "mazu_dataset.nc",
)
OUT_JSON = os.path.join(HERE, "kg_data.json")
OUT_ASSOCIATIONS_JSON = os.path.join(HERE, "kg_observational_associations.json")

# =============================================================================
# 1. NODES
# =============================================================================

# ── Data sources ─────────────────────────────────────────────────────────
DATA_SOURCES = {
    "DS1":  "Global Atmospheric Reanalysis V1.5",
    "DS2":  "Global Surface Daily Analysis",
    "DS4":  "Global SST Fusion Analysis",
    "DS8":  "Global Climate Normals (1991-2020)",
    "DS10": "Satellite Precipitation Retrieval",
}

# ── Indicators: name -> (long name, unit, source, hazard-relevance) ───────
INDICATORS = {
    "daily_precip_total":      ("Total daily precipitation", "mm", "DS2"),
    "daily_convective_precip": ("Convective precipitation", "mm", "DS2"),
    "daily_large_scale_precip":("Large-scale precipitation", "mm", "DS2"),
    "t2m_c":                   ("2 m air temperature", "degC", "DS2"),
    "tmax_c":                  ("Daily maximum temperature", "degC", "DS2"),
    "tmin_c":                  ("Daily minimum temperature", "degC", "DS2"),
    "heat_index_c":            ("Heat index (apparent temp)", "degC", "DS2"),
    "vpd_kpa":                 ("Vapour pressure deficit", "kPa", "DS2"),
    "cape":                    ("Convective available potential energy", "J/kg", "DS1"),
    "pwat":                    ("Precipitable water", "kg/m2", "DS1"),
    "ivt":                     ("Integrated vapour transport", "kg/m/s", "DS1"),
    "wind850_speed":           ("850 hPa wind speed", "m/s", "DS1"),
    "wind_shear_850_200":      ("850-200 hPa wind shear", "m/s", "DS1"),
    "daily_precip_anomaly":    ("Daily precipitation anomaly", "mm", "DS8"),
    "t2m_anomaly_c":           ("2 m temperature anomaly", "degC", "DS8"),
    "tmax_anomaly_c":          ("Max temperature anomaly", "degC", "DS8"),
    "sst_celsius":             ("Sea surface temperature", "degC", "DS4"),
    "flash_flood_risk":        ("Flash-flood risk score", "score", "derived"),
    "heatwave_day_flag":       ("Heatwave day flag", "flag", "DS8"),
    "heatwave_duration_days":  ("Heatwave duration", "days", "DS8"),
    "wind10_speed":            ("10 m wind speed", "m/s", "DS1"),
    "dewpoint_depression_c":   ("Dewpoint depression (dryness of air)", "degC", "DS2"),
}

# ── Hazards ──────────────────────────────────────────────────────────────
HAZARDS = {
    "flash_flood": "Flash Flood / Wadi Flooding",
    "heatwave":    "Extreme Heat / Heatwave",
    "dust_storm":        "Dust Storm / Strong Wind",
    "coastal":     "Coastal / Marine Risk",
}

# ── Regions: cities + geographic features (lat, lon, kind) ───────────────
REGIONS = {
    "Jeddah":       (21.5, 39.2, "city"),
    "Mecca":        (21.4, 39.8, "city"),
    "Riyadh":       (24.7, 46.7, "city"),
    "Jizan":        (16.9, 42.6, "city"),
    "Dammam":       (26.4, 50.1, "city"),
    "Taif":         (21.3, 40.4, "city"),
    "Medina":       (24.5, 39.6, "city"),
    "Abha":         (18.2, 42.5, "city"),
    "Red Sea":      (20.0, 38.5, "sea"),
    "Persian Gulf": (26.5, 51.5, "sea"),
    "Arabian Sea":  (15.5, 55.0, "sea"),
    "Empty Quarter":(19.5, 52.0, "desert"),
}

# region -> hazards it is exposed to (hand-authored domain assertion)
REGION_HAZARD = {
    "Jeddah": ["flash_flood", "coastal", "heatwave"], "Mecca": ["flash_flood", "heatwave"],
    "Taif": ["flash_flood"], "Jizan": ["flash_flood", "coastal"], "Abha": ["flash_flood"],
    "Riyadh": ["heatwave", "dust_storm"], "Medina": ["heatwave", "dust_storm"],
    "Dammam": ["heatwave", "coastal"], "Empty Quarter": ["heatwave", "dust_storm"],
    "Red Sea": ["coastal"], "Persian Gulf": ["coastal"], "Arabian Sea": ["coastal"],
}
# region -> mechanisms it is exposed to
REGION_MECH = {
    "Jeddah": ["moisture_transport", "ARST"], "Mecca": ["orographic_lift", "ARST"],
    "Taif": ["orographic_lift"], "Abha": ["orographic_lift"], "Jizan": ["moisture_transport", "orographic_lift"],
    "Riyadh": ["subtropical_high", "thermal_low"], "Medina": ["thermal_low"],
    "Dammam": ["moisture_transport"], "Empty Quarter": ["subtropical_high", "thermal_low"],
    "Red Sea": ["moisture_transport"], "Persian Gulf": ["moisture_transport"], "Arabian Sea": ["moisture_transport"],
}

# ── Mechanisms (domain knowledge) ────────────────────────────────────────
MECHANISMS = {
    "ARST":              "Active Red Sea Trough - low-level convergence over the Red Sea",
    "moisture_transport":"Red Sea / Arabian Sea moisture transport",
    "subtropical_high":  "Subtropical / continental high (heat dome)",
    "thermal_low":       "Arabian thermal low (desert heat low)",
    "orographic_lift":   "Orographic lifting over Hejaz / Asir mountains",
}

# ── Extreme samples are selected from the dataset ------------------------
EVENT_DEFS = [
    ("daily_precip_total", "flash_flood", "extreme rain",   "mm"),
    ("cape",               "flash_flood", "convective instability", "J/kg"),
    ("ivt",                "flash_flood", "vapour surge",    "kg/m/s"),
    ("tmax_c",             "heatwave",    "extreme heat",    "C"),
    ("heat_index_c",       "heatwave",    "heat stress",     "C"),
    ("wind10_speed",       "dust_storm",  "extreme wind",    "m/s"),
]
# Hazard-specific variables attached to each extreme sample. These lists are
# explicit rather than selecting the numerically largest values across
# incompatible units (which would have no scientific meaning).
SAMPLE_CONTEXT_INDICATORS = {
    "flash_flood": [
        "daily_precip_total", "cape", "ivt", "pwat", "wind850_speed",
    ],
    "heatwave": [
        "tmax_c", "heat_index_c", "vpd_kpa",
    ],
    "dust_storm": [
        "wind10_speed", "wind850_speed", "dewpoint_depression_c", "vpd_kpa",
    ],
}


def nearest_region(lat, lon):
    return min(REGIONS, key=lambda r: (REGIONS[r][0] - lat) ** 2 + (REGIONS[r][1] - lon) ** 2)


def detect_extreme_samples():
    """Select the max-value cell/date for each defining variable.

    These are dataset-derived extrema, not independently verified disaster
    occurrences. The nearest named region is descriptive geographic context,
    not evidence that the extreme occurred inside that city or region.
    """
    if not os.path.exists(DATASET):
        return {}
    ds = xr.open_dataset(DATASET)
    lat = ds.latitude.values
    lon = ds.longitude.values
    samples = {}
    for var, hazard, name, unit in EVENT_DEFS:
        if var not in ds:
            print(f"[WARN] sample-defining variable '{var}' not found; "
                  f"skipping the {hazard} extreme sample")
            continue
        a = ds[var].values
        ti, yi, xi = np.unravel_index(np.nanargmax(a), a.shape)
        date = str(ds.time.values[ti])[:10]
        la, lo = float(lat[yi]), float(lon[xi])
        region = nearest_region(la, lo)
        drivers = {}
        for d in SAMPLE_CONTEXT_INDICATORS[hazard]:
            if d not in ds:
                continue
            v = float(ds[d].values[ti, yi, xi])
            if np.isfinite(v):
                drivers[d] = round(v, 1)
        eid = f"E_{date.replace('-','')}_{var}"
        samples[eid] = {"label": f"{date[5:]} {name}", "date": date, "hazard": hazard,
                       "region": region, "peak_var": var, "peak_val": round(float(a[ti, yi, xi]), 1),
                       "unit": unit, "lat": round(la, 1), "lon": round(lo, 1), "drivers": drivers}
    ds.close()
    return samples


# Backward-compatible internal alias for older notebooks/scripts. New code
# should use detect_extreme_samples(), whose name reflects the actual method.
detect_events = detect_extreme_samples


# hazard -> mechanisms that drive it (domain knowledge)
HAZARD_MECH = {
    "flash_flood": ["ARST", "moisture_transport", "orographic_lift"],
    "heatwave":    ["subtropical_high", "thermal_low"],
    "dust_storm":        ["thermal_low"],
    "coastal":     ["moisture_transport"],
}

# =============================================================================
# 2. HAND-ENCODED EDGES
# =============================================================================

# indicator -> hazard  (grounded in flash_flood_risk formula + physics)
CONTRIBUTES_TO = {
    "flash_flood": ["daily_precip_total", "daily_convective_precip", "cape",
                    "ivt", "pwat", "wind850_speed", "daily_precip_anomaly", "flash_flood_risk"],
    "heatwave":    ["tmax_c", "t2m_c", "heat_index_c", "vpd_kpa",
                    "tmax_anomaly_c", "t2m_anomaly_c", "heatwave_day_flag", "heatwave_duration_days"],
    "dust_storm":        ["wind850_speed", "wind_shear_850_200", "vpd_kpa", "wind10_speed", "dewpoint_depression_c"],
    "coastal":     ["sst_celsius", "wind850_speed", "ivt"],
}

# mechanism -> target (indicator or hazard)  triggers
TRIGGERS = {
    "ARST":               ["ivt", "pwat", "flash_flood"],
    "moisture_transport": ["pwat", "ivt", "sst_celsius"],
    "subtropical_high":   ["tmax_c", "heatwave"],
    "thermal_low":        ["tmax_c", "vpd_kpa", "dust_storm"],
    "orographic_lift":    ["daily_precip_total", "flash_flood"],
}

# =============================================================================
# 3. DATA-DRIVEN CORRELATIONS
# =============================================================================

def compute_correlations(threshold=0.6):
    """Region-mean daily time series -> pairwise Pearson correlation.
    Returns list of (a, b, r) for |r| >= threshold.

    The result is descriptive only: no de-seasonalisation, autocorrelation
    correction, multiple-testing adjustment, or formula-ancestry exclusion is
    applied. It must not be used as causal or mechanistic evidence.
    """
    if not os.path.exists(DATASET):
        print("[WARN] dataset not found, skipping correlations")
        return []
    ds = xr.open_dataset(DATASET)
    inds = [v for v in INDICATORS if v in ds.data_vars]
    series = {}
    for v in inds:
        arr = ds[v].values  # (time, lat, lon)
        # daily region mean over valid cells
        ts = np.nanmean(arr.reshape(arr.shape[0], -1), axis=1)
        series[v] = ts
    ds.close()

    edges = []
    for a, b in itertools.combinations(inds, 2):
        x, y = series[a], series[b]
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 30:
            continue
        r = np.corrcoef(x[mask], y[mask])[0, 1]
        if np.isfinite(r) and abs(r) >= threshold:
            edges.append((a, b, round(float(r), 3)))
    return edges

# =============================================================================
# 4. BUILD GRAPH
# =============================================================================

def build():
    G = nx.DiGraph()
    samples = detect_extreme_samples()
    G.graph.update({
        "name": "MAZU Hazard Mechanism & Evidence Graph",
        "schema_version": "2.0",
        "purpose": "auditable provenance and mechanism evidence for warning explanations",
        "causal_claim_boundary": (
            "The graph organises hand-authored assertions, rule mappings, dataset "
            "observations, and literature support; it does not discover causality "
            "or improve forecast-model skill."
        ),
        "observational_associations_artifact": "kg_observational_associations.json",
    })

    def add_audited_edge(source, target, etype, *, evidence_class,
                         construction_method, source_ref, confidence,
                         review_status, eligible_for_causal_explanation=False,
                         **attrs):
        """Add an edge with mandatory provenance and claim-boundary metadata."""
        G.add_edge(
            source, target, etype=etype, evidence_class=evidence_class,
            construction_method=construction_method, source_ref=source_ref,
            confidence=confidence, review_status=review_status,
            eligible_for_causal_explanation=eligible_for_causal_explanation,
            **attrs,
        )

    # ── nodes ───────────────────────────────────────────────────────────
    for k, v in DATA_SOURCES.items():
        G.add_node(k, ntype="DataSource", label=k, desc=v)
    for k, (ln, unit, src) in INDICATORS.items():
        G.add_node(k, ntype="Indicator", label=k, desc=ln, unit=unit, source=src)
    for k, v in HAZARDS.items():
        G.add_node(k, ntype="Hazard", label=v, desc=v)
    for k, (lat, lon, kind) in REGIONS.items():
        G.add_node(k, ntype="Region", label=k, lat=lat, lon=lon, kind=kind)
    for k, v in MECHANISMS.items():
        G.add_node(k, ntype="Mechanism", label=k.replace("_", " "), desc=v)
    for k, e in samples.items():
        G.add_node(k, ntype="ExtremeSample", label=e["label"], date=e["date"], hazard=e["hazard"],
                   value=f"{e['peak_var']} {e['peak_val']} {e['unit']}",
                   location=f"{e['region']} ({e['lat']}N,{e['lon']}E)",
                   construction_method="annual_global_grid_maximum",
                   verification_status="dataset_derived_not_independently_verified_event",
                   geographic_assignment="nearest_named_region")

    # ── sourced_from : indicator -> datasource ──────────────────────────
    for ind, (_, _, src) in INDICATORS.items():
        if src in DATA_SOURCES:
            add_audited_edge(
                ind, src, "sourced_from", evidence_class="metadata_lineage",
                construction_method="hand_authored_indicator_metadata",
                source_ref="INDICATORS", confidence="medium",
                review_status="metadata_not_independently_audited",
            )

    # ── contributes_to : indicator -> hazard ────────────────────────────
    for hz, inds in CONTRIBUTES_TO.items():
        for ind in inds:
            if ind in INDICATORS:
                add_audited_edge(
                    ind, hz, "contributes_to",
                    evidence_class="rule_or_feature_mapping",
                    construction_method="hand_authored_detection_and_feature_mapping",
                    source_ref="CONTRIBUTES_TO", confidence="medium",
                    review_status="code_traceable_not_edge_level_literature_reviewed",
                )

    # ── triggers : mechanism -> indicator/hazard ────────────────────────
    for mech, targets in TRIGGERS.items():
        for t in targets:
            if t in INDICATORS or t in HAZARDS:
                add_audited_edge(
                    mech, t, "mechanistically_related_to",
                    evidence_class="expert_assertion",
                    construction_method="hand_authored_domain_mapping",
                    source_ref="TRIGGERS", confidence="low",
                    review_status="needs_edge_level_citation_review",
                    eligible_for_causal_explanation=False,
                )

    # ── driven_by : hazard -> mechanism ─────────────────────────────────
    for hz, mechs in HAZARD_MECH.items():
        for m in mechs:
            if m in MECHANISMS:
                add_audited_edge(
                    hz, m, "driven_by", evidence_class="expert_assertion",
                    construction_method="hand_authored_domain_mapping",
                    source_ref="HAZARD_MECH", confidence="medium",
                    review_status="mechanism_level_literature_partial_edge_review_pending",
                    eligible_for_causal_explanation=False,
                )

    # ── at_risk_of : region -> hazard ───────────────────────────────────
    for reg, hzs in REGION_HAZARD.items():
        for hz in hzs:
            if hz in HAZARDS:
                add_audited_edge(
                    reg, hz, "at_risk_of", evidence_class="expert_assertion",
                    construction_method="hand_authored_regional_exposure_mapping",
                    source_ref="REGION_HAZARD", confidence="low",
                    review_status="needs_region_hazard_source_review",
                )

    # ── exposed_to : region -> mechanism ────────────────────────────────
    for reg, mechs in REGION_MECH.items():
        for m in mechs:
            if m in MECHANISMS:
                add_audited_edge(
                    reg, m, "exposed_to", evidence_class="expert_assertion",
                    construction_method="hand_authored_regional_mechanism_mapping",
                    source_ref="REGION_MECH", confidence="low",
                    review_status="needs_region_mechanism_source_review",
                )

    # ── event edges : manifests_as (hazard), occurs_at (region),
    #                  driven_by_value (indicator, with real value) ──────
    for k, e in samples.items():
        add_audited_edge(
            k, e["hazard"], "sample_for_hazard",
            evidence_class="dataset_observation",
            construction_method="variable_maximum_assigned_to_predefined_hazard",
            source_ref=f"EVENT_DEFS:{e['peak_var']}", confidence="low",
            review_status="not_independently_verified_as_disaster_event",
        )
        if e["region"] in REGIONS:
            add_audited_edge(
                k, e["region"], "nearest_named_region",
                evidence_class="geographic_approximation",
                construction_method="minimum_squared_lat_lon_distance",
                source_ref="REGIONS", confidence="low",
                review_status="descriptive_only_not_administrative_containment",
            )
        # Attach the declared hazard-specific context indicators. Values with
        # different units are never ranked against each other.
        for ind, val in e["drivers"].items():
            if ind in INDICATORS:
                add_audited_edge(
                    k, ind, "observed_value", evidence_class="dataset_observation",
                    construction_method="same_grid_cell_and_date_value_lookup",
                    source_ref="mazu_dataset.nc", confidence="high",
                    review_status="computed_reproducibly", value=val,
                )

    # Compute associations for the isolated analysis artifact only. They are
    # intentionally not added to G.
    corr = compute_correlations(threshold=0.6)

    return G, corr


def main():
    G, corr = build()

    # node-link JSON for the dashboard
    data = nx.node_link_data(G, edges="links")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    association_data = {
        "name": "MAZU Observational Indicator Associations",
        "schema_version": "1.0",
        "included_in_evidence_graph": False,
        "eligible_for_causal_explanation": False,
        "method": "Pearson correlation of daily spatial-mean series",
        "threshold": "absolute_r >= 0.6",
        "limitations": [
            "not de-seasonalised",
            "no autocorrelation correction",
            "no multiple-testing adjustment",
            "formula-related variables not excluded",
            "association is symmetric and does not establish direction or causality",
        ],
        "associations": [
            {"source": a, "target": b, "pearson_r": r}
            for a, b, r in corr
        ],
    }
    with open(OUT_ASSOCIATIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(association_data, f, ensure_ascii=False, indent=2)

    # summary
    from collections import Counter
    ntypes = Counter(nx.get_node_attributes(G, "ntype").values())
    etypes = Counter(nx.get_edge_attributes(G, "etype").values())
    print("=" * 55)
    print("MAZU Hazard Mechanism & Evidence Graph")
    print("=" * 55)
    print(f"Nodes: {G.number_of_nodes()}  |  Edges: {G.number_of_edges()}")
    print("\nNode types:")
    for k, v in ntypes.items():
        print(f"  {k:12s}: {v}")
    print("\nEdge types:")
    for k, v in etypes.items():
        print(f"  {k:16s}: {v}")
    print(f"\nIsolated observational associations (|r|>=0.6): {len(corr)}")
    print("  Top 8:")
    for a, b, r in sorted(corr, key=lambda x: -abs(x[2]))[:8]:
        print(f"    {a:24s} <-> {b:24s} r={r:+.2f}")
    print(f"\n[SAVED] {OUT_JSON}")
    print(f"[SAVED] {OUT_ASSOCIATIONS_JSON}")


if __name__ == "__main__":
    main()
