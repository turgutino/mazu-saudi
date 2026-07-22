# Supplementary Methods for MCR-Precip

> This document is a preregistered implementation specification. Values prefixed with `TODO-RESULT-*` or `TODO-DECISION-*` must be resolved through the stated audit before submission.

## S1. Data contract

Each source record must preserve:

```text
source_id
source_product
source_version
source_uri
checksum
valid_start
valid_end
issue_time
availability_time
download_time
spatial_support
quality_state
licence
processing_commit
```

`issue_time` may be null for observations but is mandatory for forecast fields. A predictor is admissible only when `availability_time <= forecast_origin`. Reanalysis fields that fail this rule remain available for retrospective mechanism analysis but are excluded from operationally worded experiments.

## S2. Canonical sample schema

```text
sample_id
event_group_id
region_id
forecast_origin
lead_hours: 1 | 3 | 6
context_start
context_end
target_start
target_end
input_manifest_ids[]
availability_mask
reference_product
observation_state: observed | not_observed | not_observable | conflicting
extreme_threshold_mm
occurrence_target
accumulation_target_mm
object_ids[]
split_id
```

The primary spatial grid is 0.1°. All extensive variables are conservatively regridded where possible; categorical masks use nearest-neighbour mapping. Accumulated precipitation is never interpolated as an instantaneous rate without explicit conversion.

## S3. Region definitions

| Region | Bounding box | Intended regimes | Independent-observation audit |
|---|---|---|---|
| Arabian Peninsula | 12–32° N, 34–60° E | Red Sea convection, coastal convergence, interior dryland storms | ISD/NCM candidates and FYMERG |
| Southwestern North America | 20–40° N, 120–100° W | monsoon convection, terrain and organized systems | ISD and MRMS in covered US cells |
| Interior Australia | 35–15° S, 120–145° E | tropical incursions, dryline and continental convection | Bureau/public gauge candidates; audit required |
| Southern Africa | 35–15° S, 10–35° E | plateau convection and moisture transport | ISD/public gauge candidates; audit required |

The dryland mask uses aridity index below 0.65. The precise dataset version, coastline mask and cell list are frozen in `dryland_mask_manifest.parquet`. If fewer than three regions pass the independent-observation audit, the Nature Communications claim is stopped and the scope is reduced.

## S4. Observation states

- `observed`: an admissible sensor sampled the target support with passing quality.
- `not_observed`: an admissible sensor sampled the support and reported no threshold exceedance.
- `not_observable`: no admissible measurement can establish absence.
- `conflicting`: admissible sources disagree beyond the registered tolerance.

Only `observed` and `not_observed` enter the primary high-confidence binary evaluation. `not_observable` is excluded. `conflicting` is reported separately and used in sensitivity analysis.

## S5. Threshold estimation

1. Convert each half-hourly record to millimetres over its represented interval.
2. Form right-closed rolling 1-, 3- and 6-hour accumulations without crossing missing intervals.
3. In the 2001–2018 reference window, calculate cell-month percentiles from wet periods above the product detection floor.
4. Require a minimum `TODO-DECISION-WET-SAMPLES` wet periods per cell-month; otherwise pool with the registered climate neighbourhood.
5. Set thresholds to `max(P99.9, 10/20/30 mm)` for 1/3/6 hours.
6. Freeze threshold arrays before model development.

Sensitivity experiments use P99, P99.5 and P99.9. They do not replace the primary threshold after test inspection.

## S6. Event objects

Exceedance cells are connected with an eight-neighbour rule. Consecutive objects are matched using overlap after one-cell dilation and a maximum motion-consistent displacement derived from the preceding six-hour sequence. Candidate matches with equal score are resolved deterministically. Each connected track receives one `event_group_id`; all overlapping forecast samples inherit it.

Object evaluation reports centroid displacement, intersection-over-union, maximum intensity error, area error, onset error and duration error. Pixel-level and object-level outcomes remain separate.

## S7. Input features

### Common causal core

- 12 half-hourly precipitation frames ending at forecast origin;
- precipitation quality and observation-age frames;
- elevation, slope, aspect, terrain curvature and land–sea mask;
- cyclical month and local-solar-time encodings;
- admissible archived wind, moisture, CAPE and precipitable-water fields when available.

### Mechanism state

- storm motion estimated from at least two registered algorithms, with disagreement retained as uncertainty;
- horizontal wind and integrated vapour transport magnitude/direction;
- CAPE, CIN, precipitable water and moisture convergence;
- upslope transport and terrain-alignment score;
- recent object coherence, growth rate and decay rate;
- lead time and complete modality mask.

Absolute region identifiers are prohibited. Coordinate channels must be crop-relative and tested by a region-classification probe; if the probe reconstructs region above `TODO-DECISION-REGION-PROBE`, coordinates are removed or randomized.

## S8. Experts

All experts consume a shared encoded tensor and return equal-dimensional latent fields.

- **Advection:** differentiable semi-Lagrangian or deformable transport initialized by admissible motion fields.
- **Convection:** local multi-scale kernels with max/top-k preservation and instability conditioning.
- **Orography:** terrain-relative directional message passing using slope and upslope flow.
- **Persistence–decay:** gated temporal continuation with no explicit directional transport.

The primary four-expert model and all matched baselines use the same encoder, decoder width and output heads. A compute ledger records parameters, multiply–accumulate estimates, training steps, memory and inference time.

## S9. Applicability priors

Priors are normalized non-negative scores computed without the outcome:

```text
pi_adv  <- coherent storm motion, wind alignment, transport strength
pi_conv <- instability, moisture availability, local growth
pi_oro  <- moist upslope flow, slope, terrain alignment
pi_per  <- recent coherent rainfall, weak new forcing, slow decay
```

Quality masks determine whether each prior is eligible. Ineligible priors contribute no KL term. Prior thresholds and monotone transforms are chosen from physical literature and source-region validation only, then frozen.

## S10. Counterfactual suite

| Counterfactual | Eligibility | Expected router response | Negative control |
|---|---|---|---|
| Rotate transport 90° | coherent non-zero transport | rotate/reduce downstream advection influence | rotate an unused copied vector |
| Reduce CAPE/PWAT | convectively eligible sample | reduce convective contribution or increase uncertainty | perturb a distant static channel |
| Flatten terrain | terrain-influenced sample | reduce orographic contribution | flatten terrain over flat cells |
| Mask recent rain | complete recent sequence | reduce persistence evidence and increase uncertainty | mask an already missing frame |

The loss penalizes directional violations of router weights and selected forecast summaries. It does not require a counterfactual rainfall target. Effect sizes are reported only on eligible samples and compared with negative controls.

## S11. Missingness scenarios

1. Full recent-precipitation channel unavailable.
2. Contiguous 1-, 2- or 3-hour gaps.
3. Dynamic atmospheric modality unavailable.
4. Terrain or static-data corruption.
5. Region-specific empirical missingness replay.
6. FYMERG absent outside its 2025 coverage.

Independent random-pixel dropout is a diagnostic, not the primary missingness benchmark. No unavailable short-duration sensor may be replaced by a daily total and presented as equivalent information.

## S12. Baseline fairness

Each baseline receives exactly the input modalities allowed by its registered variant. Hyperparameter budgets are fixed by number of trials and total training steps. Deep baselines use the same training years, validation years, crop sampler, class balancing, seeds and early-stopping metric. Optical flow uses only past precipitation and is not penalized for lacking atmospheric fields; an additional input-matched comparison isolates this difference.

## S13. Calibration

Temperature, beta and isotonic calibration are compared on source validation data. The rule for selecting the primary calibrator is fixed before target-region evaluation. Reliability uses equal-mass and fixed-width bins, with bin counts and uncertainty intervals disclosed. Brier Skill uses the registered monthly source climatology reference.

## S14. Statistical protocol

- Resampling unit: `event_group_id`.
- Primary interval: paired percentile bootstrap, with TODO-RESULT-BOOTSTRAP replicates.
- Primary comparison: MCR-Precip versus strongest matched-compute baseline selected on source validation.
- Region consistency: same direction in at least three of four held-out regions.
- Reliability guardrail: no material deterioration in worst-region Brier score or high-probability calibration.
- Secondary tests: false-discovery-rate correction within each declared hypothesis family.

No pixel is treated as an independent replicate. Seeds quantify optimization variability but do not replace event-level uncertainty.

## S15. Result artifact contract

Every `TODO-RESULT-*` replacement must point to a JSON, CSV, Parquet or NetCDF artifact containing:

```text
claim_id
metric
estimate
interval_low
interval_high
split_id
region
lead_hours
model_bundle_id
experiment_manifest_id
code_commit
generated_at
```

The manuscript build fails if a result token is replaced without a matching claim-evidence record, or if an artifact was generated from an unapproved test version.
