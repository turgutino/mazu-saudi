# Reviewer Risk Register

| Priority | Likely criticism | Why it is credible | Required mitigation | Stop or downgrade condition |
|---|---|---|---|---|
| P0 | IMERG is not ground truth | retrieval errors may be learned and rewarded | independent gauge/radar/FYMERG evaluation; observation states; intensity-stratified agreement | fewer than three regions have credible independent evaluation |
| P0 | Reanalysis inputs violate forecast availability | ERA5 is produced after valid time and assimilates future information | formal availability contract; archived forecast/reforecast for operational claims; retrospective experiments labelled | no forecast-origin-safe dynamic fields but paper claims operational forecasting |
| P0 | One-year MAZU cannot support climatology | 2025 lacks interannual variability and stable tail estimates | use 2001–2024 public common core; MAZU only for pretraining/modality tests | thresholds or cross-year claims rely on 2025 MAZU |
| P0 | Geographic OOD is contaminated by global pretraining | unlabeled target-region inputs can leak geography | strict target-excluded protocol plus separately labelled transductive protocol | only transductive results are available |
| P0 | Mechanism experts are renamed generic branches | MoE, graphs and physics features already exist | matched identical-expert controls; applicability constraints; falsifiable counterfactual tests | gain disappears against unconstrained identical-expert MoE |
| P1 | Router interpretation is post-hoc | attention or expert weights need not be causal | eligible directional interventions and negative controls | violation rate does not improve or is unrelated to OOD performance |
| P1 | Threshold choice manufactures performance | rare-event metrics vary with percentile and floor | preregister primary threshold; sensitivity grid; frozen climatology | conclusion holds at only one inspected threshold |
| P1 | Pixel samples inflate significance | neighbouring cells and windows are dependent | event grouping and event-block bootstrap | event grouping cannot be made stable |
| P1 | Abstention hides severe events or regions | average risk–coverage can be unfair | conditional coverage by region/intensity; mandatory-prediction metrics retained | high-intensity events are preferentially rejected |
| P1 | Apparent gain is model size or compute | conditional models add parameters | matched parameters/FLOPs/training budget and latency ledger | no benefit at matched compute |
| P1 | Four boxes are arbitrary | region choice may encode desired outcome | aridity mask, mechanism rationale, full cell manifest and leave-one-region-out rotation | results driven by one region only |
| P2 | 0.1° cannot resolve short-lived cells | spatial smoothing can dominate labels and forecasts | independent higher-resolution subset; neighbourhood/object verification | claimed fine-scale mechanism is below reference resolution |
| P2 | Counterfactual inputs are physically inconsistent | rotating wind alone can create impossible states | directional router tests only; no claim of synthetic truth; matched controls | manuscript claims full causal atmospheric simulation |
| P2 | Results do not justify Nature Communications breadth | method improvement alone may be incremental | establish general dryland failure pattern, mechanism evidence and prospective significance | only a small average score gain remains |

## Editorial framing guardrails

- Do not use “first” unless a final systematic search supports it.
- Do not call the uniform satellite reference “ground truth”.
- Do not call a transductive experiment zero-shot or geographically blind.
- Do not use “operational” for retrospective analysis-field experiments.
- Do not infer flood occurrence, damage or warning value from rainfall alone.
- Do not retain the strong title if independent observations contradict the main result.
