# Publication Workplan: Global Dryland Extreme Precipitation

## Outcome

The project advances through evidence gates rather than a fixed promise to submit to Nature Communications. The target is retained only while data quality, cross-region effects, mechanism tests and reproducibility satisfy the gates below.

## Gate 0: feasibility audit (weeks 1–4)

### Work

- Freeze four region boxes and candidate dryland-mask version.
- Inventory IMERG 2001–2024, hourly gauges, MRMS coverage, FYMERG 2025 and forecast/reforecast archives.
- Sample at least 20 extreme candidates per region.
- Measure timing, distance, intensity and availability agreement between IMERG and independent observations.
- Estimate storage, download, preprocessing and GPU budgets on a one-month sample.

### Deliverables

- `source_inventory.parquet` and licence table.
- Four regional observation-completeness reports.
- Eighty-event audit sheet.
- Data-volume and compute estimate.
- Written go/reduce/stop decision.

### Pass rule

At least three regions must provide credible independent event evaluation and the common-core data must be computationally feasible. Otherwise reduce to MENA or reposition as a satellite-reference/application study.

## Gate 1: pilot benchmark (months 2–3)

### Work

- Process 2018–2024 first, then confirm thresholds against the 2001–2018 climatology sample.
- Implement observation states, rolling accumulations, object tracking and event-group splits.
- Freeze a pilot train/validation/test manifest.
- Map 2025 MAZU/FYMERG to the common schema without using MAZU for climatology.
- Run leakage, unit, missingness and cross-source alignment tests.

### Deliverables

- Versioned pilot dataset card.
- Frozen event index and region manifests.
- Reproducible preprocessing environment.
- Station/satellite comparison report.

### Pass rule

Event extraction must be stable under small threshold changes; split leakage must be zero; independent-reference error must be quantified rather than assumed negligible.

## Gate 2: trustworthy baselines (months 3–5)

### Work

- Train climatology, persistence, optical flow, HGB/XGBoost, ConvLSTM/U-Net and graph baselines.
- Run temporal and leave-one-region-out evaluation at 1/3/6 hours.
- Complete prevalence-matched and object-based error analysis.
- Freeze the strongest matched-information and matched-compute baselines before developing MCR-Precip.

### Pass rule

Proceed to the method paper only if geographic shift produces reproducible failure modes that are not explained solely by event prevalence or reference-product quality. Otherwise publish the benchmark/error analysis or revise the scientific question.

## Gate 3: MCR-Precip (months 5–9)

### Work

- Implement four experts and a region-blind mechanism router.
- Add applicability priors, counterfactual constraints and uncertainty output in that order.
- Run matched-capacity controls, all ablations and at least the frozen minimum number of seeds.
- Test strict MAZU target exclusion separately from label-free transductive pretraining.

### Pass rule

The primary effect must have an event-bootstrap interval excluding zero, agree in at least three held-out regions and preserve worst-region calibration. Counterfactual violation reduction must survive eligible-case and negative-control analysis.

## Gate 4: reliability and independent verification (months 8–11)

### Work

- Fit source-only calibrators and freeze abstention rules.
- Replay empirical missingness and full-modality outages.
- Report conditional risk–coverage by region and intensity.
- Re-evaluate all major claims on the high-confidence independent-observation subset.
- Complete source-data files and computational ledger.

### Pass rule

The principal result must reproduce against independent observations. Abstention must not preferentially remove the strongest events or a single region.

## Gate 5: prospective evaluation (minimum months 6–18)

### Work

- Archive FY satellite, international forecast and weather-foundation-model outputs continuously with issue, availability and valid times.
- Register the prospective set before model freeze.
- Run one locked evaluation after sufficient events accumulate.
- Treat insufficient event count as inconclusive, not as failure or permission to tune.

## Manuscript freeze and submission

1. Resolve all `TODO-REFERENCE-*` records against primary publisher pages.
2. Replace `TODO-RESULT-*` only from approved machine-readable artifacts.
3. Generate all figures, tables and source data from one frozen code commit.
4. Reproduce the full paper in a clean environment.
5. Complete data/code availability, licences, authorship, competing interests and reporting checklists.
6. Conduct an internal red-team review using `reviewer_risk_register.md`.
7. Select venue according to evidence:
   - satellite-reference/2025-only: application or data venue;
   - multi-year plus independent regional validation: strong AI-for-Earth or remote-sensing venue;
   - cross-continental finding, mechanism evidence, reliable OOD and prospective result: Nature Communications candidate.

## Immediate next actions

1. Build the Gate 0 source inventory before downloading the full archive.
2. Audit 20 events in the Arabian Peninsula and southwestern North America first because FYMERG and MRMS offer complementary reference checks.
3. Estimate IMERG storage and processing cost on one month from each region.
4. Verify whether archived forecast/reforecast fields contain the required wind, moisture, CAPE and precipitable-water variables at admissible issue times.
5. Do not implement the deep model until the observation and baseline gates pass.
