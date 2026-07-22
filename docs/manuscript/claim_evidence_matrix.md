# MCR-Precip Claim–Evidence Matrix

This file is the control surface for manuscript claims. A claim may move from **proposed** to **supported** only when every required artifact is frozen and independently reproducible. Result tokens in the manuscript must map to an entry here.

| Claim ID | Proposed claim | Required evidence | Primary comparison | Passing rule | Manuscript tokens | Status |
|---|---|---|---|---|---|---|
| C1 | Dryland regions exhibit mechanism-state distribution shift beyond prevalence differences | four-region audit; prevalence-matched analysis; mechanism-state distances; hierarchical event analysis | region pairs and prevalence-matched subsets | residual shift is measurable with event-level uncertainty; no causal wording | `TODO-RESULT-DATA-*`, `TODO-RESULT-OOD-04/05` | proposed |
| C2 | Conventional models degrade under geographic OOD | all registered baselines on frozen leave-one-region-out splits | matched temporal versus geographic tests | degradation reproduced in at least 3 regions and not caused solely by prevalence | `TODO-RESULT-OOD-*` | proposed |
| C3 | MCR-Precip improves cross-region prediction | MCR, unconstrained MoE and matched dense model; 4 held-out regions; 3 horizons | strongest source-validation-selected matched-compute baseline | direction agrees in >=3 regions; pooled event-bootstrap 95% CI excludes 0 | `TODO-RESULT-MCR-*`, `TODO-RESULT-MATCHED-*` | proposed |
| C4 | Improvement is not parameter-count gain | parameter/FLOP/step ledger; matched dense and identical-expert MoE | MCR versus matched controls | main improvement remains under compute matching | `TODO-RESULT-MATCHED-*` | proposed |
| C5 | Mechanism priors and counterfactuals contribute | full ablation family with fixed seeds and splits | full MCR versus no-prior/no-counterfactual variants | paired event effects and violation-rate reduction support both components | `TODO-RESULT-ABLATION-*`, `TODO-RESULT-CF-*` | proposed |
| C6 | Probabilities remain reliable in held-out regions | Brier, NLL, reliability, high-probability bins, worst-region score | calibrated MCR versus calibrated baselines | no material worst-region degradation; source-only calibration | `TODO-RESULT-CAL-*` | proposed |
| C7 | Selective prediction controls missing-sensor risk | empirical missingness replay; block/channel ablations; conditional coverage | MCR uncertainty versus dense entropy and MoE uncertainty | lower risk at matched coverage without discarding strongest events/one region | `TODO-RESULT-SELECTIVE-*`, `TODO-RESULT-MISSING-*` | proposed |
| C8 | Satellite-reference improvements reflect physical rainfall skill | independent gauges/radar/FYMERG with observation-state audit | ranking on IMERG versus independent subset | main direction reproduces; disagreement disclosed | `TODO-RESULT-OBS-*`, `TODO-RESULT-INDEPENDENT-*` | proposed |
| C9 | MAZU adds transfer value but not climatology | strict exclusion and label-free transductive protocols reported separately | no MAZU, strict MAZU and transductive MAZU | no geographic-blind wording for transductive result | `TODO-RESULT-MAZU-*` | proposed |
| C10 | Error sources are physically interpretable | preregistered case sampler and object diagnostics | model and observation failure categories | examples selected by rule, including unfavorable cases | `TODO-RESULT-FAIL-*` | proposed |

## Required artifact layout

```text
experiments/<experiment_manifest_id>/
  manifest.json
  metrics/region_horizon_metrics.parquet
  metrics/event_predictions.parquet
  metrics/bootstrap_differences.parquet
  calibration/reliability_bins.parquet
  routing/counterfactual_responses.parquet
  missingness/risk_coverage.parquet
  observations/independent_validation.parquet
  compute/ledger.json
  figures/source_data/
```

## Replacement rule

For each manuscript token:

1. Record its `claim_id`, artifact path, metric filter and formatting rule.
2. Verify artifact `code_commit`, `split_id` and `model_bundle_id` against the approved manifest.
3. Generate the text value automatically; do not type a result number by hand.
4. Change claim status only after a second clean-environment reproduction.
5. Preserve failed or contradictory results and revise the claim instead of changing the test.
