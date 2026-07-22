# Figure and Table Plan

## Main figures

| Item | Scientific purpose | Panels | Source artifact | Gate |
|---|---|---|---|---|
| Figure 1 | Establish benchmark, observation quality and shift | regions; data tracks; event counts; mechanism distributions | dataset audit and event index | three regions pass independent-observation audit |
| Figure 2 | Demonstrate conventional OOD failure | temporal/OOD metrics; calibration shift; three failure modes | baseline result bundle | C1 and C2 support a non-trivial problem |
| Figure 3 | Present method and primary evidence | architecture; constraints; paired event effects; region×lead matrix | MCR and matched baselines | C3 and C4 pass |
| Figure 4 | Show tail, probability and spatial behaviour | PR; reliability; intensity strata; spatial tolerance | evaluation bundle | calibrated predictions frozen |
| Figure 5 | Test missing sensors and abstention | scenarios; risk–coverage; conditional coverage; router response | missingness bundle | C7 passes fairness guardrails |
| Figure 6 | Falsify mechanism interpretation and disclose failures | violation rates; three counterfactuals; four failures | routing and case bundle | C5 passes; cases selected by rule |

## Main tables

| Item | Contents | Source artifact |
|---|---|---|
| Table 1 | region, period, grid cells, events, base rate, station/radar matches and completeness | dataset audit |
| Table 2 | primary leave-one-region-out metrics for MCR and strongest controls | region-horizon metrics |
| Table 3 | ablations, parameters, FLOPs, latency and memory | ablation metrics and compute ledger |

## Supplementary items

- Supplementary Figure 1: complete availability and quality maps.
- Supplementary Figure 2: threshold sensitivity at P99/P99.5/P99.9.
- Supplementary Figure 3: satellite–gauge/radar agreement by intensity and terrain.
- Supplementary Figure 4: all baseline results by seed, region and horizon.
- Supplementary Figure 5: expert count and capacity controls.
- Supplementary Figure 6: all reliability diagrams and bin uncertainty.
- Supplementary Figure 7: neighbourhood scores at 10/25/50 km.
- Supplementary Figure 8: counterfactual eligibility and negative controls.
- Supplementary Figure 9: missingness replay frequency and conditional coverage.
- Supplementary Figure 10: all preregistered failure cases.
- Supplementary Table 1: source products, versions, licences and checksums.
- Supplementary Table 2: exact features and availability semantics.
- Supplementary Table 3: full metric matrix.
- Supplementary Table 4: hyperparameters and training budgets.
- Supplementary Table 5: statistical tests and corrected p-values.

## Figure integrity rules

- Every plotted value must be present in a source-data file.
- Maps must state projection, temporal support and missingness.
- Colour scales comparing models must be identical.
- Reliability figures must show sample counts or uncertainty.
- Case panels must show input availability and reference conflicts.
- Architecture graphics may illustrate intended computation but cannot be presented as empirical evidence.
