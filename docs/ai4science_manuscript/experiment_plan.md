# AI4Science Experiment Plan: Cross-Scale Dryland Rainfall Regimes

## Scientific objective

Determine whether reproducible cross-scale atmospheric regimes govern the conversion of large-scale forcing into 1–6-hour rainfall extremes across global drylands, and whether those regimes explain historical forecast blind spots beyond region, season, intensity and observation quality.

The plan does not require a novel prediction architecture. AI components are selected for stable scientific discovery, not leaderboard performance.

## Experiment 0: feasibility and collision audit (weeks 1–4)

### Questions

- Can at least three dryland regions support sub-daily events with independent observation checks?
- Are the required pressure-level and forecast fields available at adequate temporal resolution?
- Does the proposed question go beyond the known daily-scale role of Rossby-wave breaking and known hourly temperature scaling?

### Work

- Audit 20 events per region using IMERG and available gauges/radar/FYMERG.
- Calculate data volume for 48-hour, multi-level event windows.
- Implement objective diagnostics on eight representative events.
- Produce a final literature collision table for each proposed physical claim.

### Pass rule

Proceed globally only if three regions pass observation audit, physical diagnostics are computationally feasible, and the novelty is demonstrably sub-daily/cross-scale rather than a repeat of daily driver attribution.

## Experiment 1: event catalogue and temporal-scale gap (months 2–4)

### Data

- IMERG Final half-hourly precipitation, 2001–2024.
- Independent hourly gauges and radar–gauge fields where available.
- Frozen dryland mask, terrain and observation states.

### Analyses

- Extract P99.9 plus absolute-floor 1/3/6-hour objects.
- Group overlapping windows into independent weather systems.
- Quantify morphology: initiation, growth, translation, peak, area and duration.
- Match daily totals and test whether sub-daily evolution remains heterogeneous.

### Pass rule

Observation-quality-matched events with similar daily totals must exhibit stable, scientifically meaningful sub-daily diversity. Otherwise the proposed temporal-scale gap is unsupported.

## Experiment 2: blind regime discovery (months 4–6)

### Discovery protocol

- Discovery years: 2001–2018.
- Confirmation years: 2019–2024.
- External sensor confirmation: MAZU-rich 2025.
- Candidate cluster counts: 2–10.
- Representation families: PCA/EOF baseline, topology-preserving baseline, established self-supervised spatiotemporal encoder.
- Partition families: k-means/GMM plus spectral or density alternative.

### Prohibited selection signals

- forecast errors;
- withheld physical labels or objective regime catalogues;
- continent/country identity;
- impacts or model performance.

### Acceptance metrics

- event-bootstrap co-assignment stability;
- adjusted mutual information across representation/partition families;
- held-out-year prototype recovery;
- leave-one-continent recovery;
- ambiguous/unassigned rate;
- continent leakage probe.

### Pass rule

At least two non-trivial regimes must recur in three regions and reproduce in the confirmation years. If partitions are primarily geographic or algorithm-specific, stop the mechanism-atlas claim.

## Experiment 3: independent physical validation (months 6–9)

### Withheld diagnostics

- Rossby-wave-breaking/PV streamer and cutoff catalogues;
- vertically integrated moisture-flux convergence;
- omega and ascent profiles;
- CAPE/CIN tendency and instability release;
- low-level convergence and terrain-relative moisture transport;
- optional Lagrangian moisture-source diagnostics.

### Tests

- Event-relative composites with event-block uncertainty.
- Timing of diagnostics relative to initiation and peak.
- Budget closure and residual reporting.
- Cross-reanalysis and cross-precipitation-product sensitivity.
- Negative-control diagnostics and neutral regime names when evidence is weak.

### Pass rule

A physical regime name requires at least two independent coherent diagnostics, correct temporal ordering and replication in at least three regions. AI attribution alone never passes this gate.

## Experiment 4: matched conversion analysis (months 8–10)

### Design

- Match extreme events, near misses and non-intensifying rainfall objects on large-scale forcing.
- Balance season, region, PV configuration, IVT, synoptic ascent, antecedent rain and observation quality.
- Test low-level convergence, convective inhibition, terrain alignment and organization as local differentiators.

### Robustness

- common-support and balance plots;
- alternative distance/propensity specifications;
- lag-reversed outcomes;
- negative-control variables;
- unmeasured-confounding sensitivity;
- region-by-region replication.

### Wording rule

Without an intervention, natural experiment or process-model perturbation, report conditional association rather than causal effect.

## Experiment 5: forecast blind spots (months 9–12)

### Data

- GEFSv12 reforecast/reanalysis where variables and lead times are suitable.
- TIGGE or another consistent archive for later periods.
- Optional operational/weather-foundation-model archive reported separately by generation.

### Outcomes

- missed initiation;
- centroid displacement;
- peak-intensity error;
- footprint and duration error;
- Brier/reliability and ensemble spread–error.

### Statistical model

Compare hierarchical out-of-sample models containing region, season, intensity, footprint, observation quality, lead and forecast generation, with and without frozen regime identity. Report partial deviance, likelihood improvement and event-block uncertainty.

### Pass rule

Regime must explain residual error beyond obvious covariates, reproduce in at least two forecast systems or generations, and not be driven by one region or observation product.

## Experiment 6: confirmation and red-team (months 11–14)

- Open the 2019–2024 confirmation results only after regime and diagnostic specifications are frozen.
- Project 2025 MAZU-rich events without re-estimating multi-year frequencies.
- Repeat all headline results using an alternate precipitation product/reanalysis where possible.
- Conduct a meteorologist-led blind interpretation of neutral regime composites.
- Search for cases that contradict each proposed mechanism.

## Publication decision

### Nature Communications candidate

- stable cross-continental regimes;
- new sub-daily conversion insight beyond known daily drivers;
- independent physical-budget support;
- matched transition evidence;
- regime-specific forecast blind spots beyond geography and intensity;
- confirmation across time, observations and sensors.

### Strong Earth-system/AI4Science paper

- stable regimes and physical validation, but incomplete forecast archive or only three regions.

### Benchmark/data paper

- valuable event catalogue and diversity analysis, but no stable new mechanism.

### Stop condition

- clusters reflect geography/product artifacts;
- physical diagnostics do not independently support them;
- forecast-error differences disappear after intensity and quality matching.

## Immediate actions

1. Execute the shared Gate 0 source inventory once for both papers.
2. Implement a pilot on Arabian Peninsula and southwestern North America, 2018–2024.
3. Test objective PV/wave-breaking, moisture-flux-convergence and terrain-alignment diagnostics on eight events.
4. Compare daily-matched events to verify that a genuine sub-daily question exists.
5. Recruit an atmospheric-dynamics collaborator before assigning physical names to AI regimes.
