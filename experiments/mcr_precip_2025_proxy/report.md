# MCR-Precip Saudi 2025 real-data proxy comparison

> This is a 24-hour `flash_flood_risk>=2` proxy-label experiment, not an
> independent flash-flood truth evaluation or an operational warning result.

- Generated: `2026-07-28T17:20:48.463605+00:00`
- Split: train through 2025-05-31; validation 2025-06; test 2025-07-01 onward
- Grid: stride 4 ([40, 55])
- Seeds: [42, 43, 44]
- Terrain available: True
- Platt calibration and thresholds are fitted on June validation data;
  July–December is test-only.

| Model | PR-AUC | CSI | POD | FAR | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|
| HGB, matched inputs | 0.0759 | 0.0465 | 0.0609 | 0.7490 | 0.0050 | 0.0028 |
| MoE, no mechanism prior | 0.0590 | 0.0483 | 0.2798 | 0.9341 | 0.0060 | 0.0037 |
| MCR, mechanism prior | 0.0542 | 0.0446 | 0.3103 | 0.9502 | 0.0069 | 0.0049 |

## Interpretation boundary

- The MCR run uses the applicability-prior constraint only; real-data
  counterfactual training is not included in this bounded experiment.
- Consolidated inputs lack vector wind, so advection direction is unavailable.
- The historical HGB number is included as context only because it uses a
  different stride and no independent validation threshold.
- A gain is competition evidence only if it is stable across seeds and does
  not trade lower PR-AUC/Brier reliability for a test-tuned operating point.

## Decision

- Status: `research_only_not_adopted`
- MCR did not beat the matched HGB on the preregistered joint gate; keep it as an implemented research prototype and do not use it as a competition performance claim.
