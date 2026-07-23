# Global Dryland Extreme Precipitation: Two-Paper Portfolio

This project maintains two independent manuscripts on a shared, versioned event dataset. They answer different questions and must not divide one empirical claim into two publications.

## Paper A: computer-method and reliable-prediction track

- **Working title:** *Mechanism-constrained routing enables reliable extreme precipitation prediction across global drylands*
- **Primary question:** Does mechanism-constrained conditional computation improve 1/3/6-hour prediction, calibration and selective reliability under geographic and sensor shift?
- **Primary contribution:** MCR-Precip method, matched-compute comparisons, ablations, counterfactual routing and risk–coverage evaluation.
- **Package:** [MCR-Precip manuscript and experiment plan](manuscript/README.md).

## Paper B: AI4Science mechanism-discovery track

- **Working title:** *Cross-scale atmospheric regimes govern sub-daily rainfall extremes across global drylands*
- **Primary question:** Which reproducible cross-scale atmospheric regimes convert large-scale forcing into local sub-daily rainfall extremes, and which regimes create systematic forecast blind spots?
- **Primary contribution:** a cross-continental mechanism atlas, independent physical-budget validation, matched-event evidence and regime-conditioned forecast-error discovery.
- **Package:** [AI4Science manuscript and experiment plan](ai4science_manuscript/README.md).

## Shared assets

- 2001–2024 extreme-rainfall event registry and observation-quality states.
- Four dryland macro-regions, aridity mask and immutable event grouping.
- IMERG uniform reference and independent gauge/radar/FYMERG validation layers.
- Source, availability-time, licence, checksum and processing provenance.

Shared assets must receive one version and one canonical description. Each manuscript cites the dataset release or companion paper instead of copying long construction claims.

## Non-overlap contract

| Boundary | Paper A | Paper B |
|---|---|---|
| Main outcome | forecast skill, calibration, robustness | scientific regimes, physical transitions, forecast-error structure |
| AI novelty | new routing/constraint method | no architecture novelty required; AI is a discovery instrument |
| Main comparator | matched prediction models | conventional regime definitions, clustering stability, physical diagnostics |
| Counterfactual role | tests router behaviour | matched events/negative controls test scientific associations |
| Forecast archive | target for prediction evaluation | object whose errors are explained |
| MAZU 2025 | pretraining/modality/OOD track | independent regime confirmation and sensor-shift check |
| Forbidden claim | discovering a new atmospheric mechanism from model weights alone | claiming a better forecast model as the scientific discovery |

The same figure, result table or primary statistical comparison cannot appear as a headline result in both papers. Any shared validation must be labelled as dataset characterization and cross-cited.

## Recommended order

1. Build and freeze the common event dataset.
2. Execute Paper B first through its mechanism-stability gate. A scientific regime atlas can inform, but must not be defined by, MCR-Precip.
3. Freeze Paper B regime definitions before using them as Paper A evaluation strata.
4. Develop Paper A only if its method gain survives matched-compute, independent-observation and OOD gates.
5. Disclose both manuscripts and their overlap to editors whenever they are simultaneously under consideration.
