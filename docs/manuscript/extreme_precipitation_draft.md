# Mechanism-constrained routing enables reliable extreme precipitation prediction across global drylands

**Article type:** Article
**Target journal:** Nature Communications
**Draft status:** Results-ready manuscript; not submission-ready
**Authors:** TODO-AUTHOR-01
**Affiliations:** TODO-AFFILIATION-01
**Correspondence:** TODO-CORRESPONDENCE-01

> **Draft integrity notice.** This manuscript defines the intended scientific claims and the experiments required to support them. No cross-regional MCR-Precip experiment has yet been completed. Every unknown number or empirical conclusion is marked with a `TODO-RESULT-*` token. These tokens must be replaced only from a frozen, reproducible experiment artifact recorded in the [claim–evidence matrix](claim_evidence_matrix.md). The current 2025 Saudi MAZU subset is not evidence for the cross-continental claims below.

## Abstract

Short-duration extreme rainfall is difficult to predict in drylands, where sparse observations, abrupt convective growth and terrain-controlled propagation create shifts that are poorly represented by average forecast scores. We introduce MCR-Precip, a mechanism-constrained routing framework that combines advection, local convective growth, orographic enhancement and persistence–decay experts without using region identity to select them. The router is regularized by observable mechanism-applicability priors and by counterfactual perturbations of wind, instability, terrain and sensor availability. We evaluate 1-, 3- and 6-hour probabilistic forecasts across the Arabian Peninsula, southwestern North America, interior Australia and southern Africa using a 2001–2024 common-core dataset and a separate 2025 MAZU-rich transfer track. Relative to TODO-RESULT-BASELINE, MCR-Precip changes event-level precision–recall skill by TODO-RESULT-ABSTRACT-01 and Brier skill by TODO-RESULT-ABSTRACT-02 under leave-one-region-out evaluation. Under missing sensors, selective prediction changes risk at matched coverage by TODO-RESULT-ABSTRACT-03. Counterfactual tests show TODO-RESULT-ABSTRACT-04. These results would establish whether physically testable routing, rather than model scale alone, can improve reliable extreme-rainfall prediction across global drylands.

## Introduction

Short-duration extreme rainfall causes disproportionate disruption in drylands. Long rain-free periods can be interrupted by rapidly developing convection, narrow rain cores and terrain-locked storms. These systems are difficult to represent on coarse grids and difficult to verify where gauges and weather radars are sparse. The forecasting problem is therefore not simply to reduce mean precipitation error. A useful model must preserve rare local extremes, transfer across different dryland regimes, issue calibrated probabilities, and recognize when missing observations make a prediction unsafe.

Recent machine-learning weather systems have substantially improved global medium-range prediction and probabilistic forecast skill [1–3]. Radar-based generative nowcasting has also produced sharper short-range rainfall fields than deterministic regression in well-observed regions [4,5]. These advances do not by themselves resolve the dryland problem. Global models can smooth small convective cells; radar-centered nowcasting assumes an observing network that is absent across much of the study domain; and aggregate scores can conceal failures on rare, spatially displaced events. Distribution shift is especially important because a model trained in one continent may associate season, terrain or sensor characteristics with rainfall for reasons that do not transfer to another.

Extreme-rainfall prediction also creates a verification problem. Satellite precipitation estimates provide globally consistent coverage but are retrieval products rather than absolute ground truth. Gauge observations are more direct but sparse and affected by representativeness and reporting errors. Radar–gauge mosaics can provide high-resolution reference fields in a subset of regions but are not globally homogeneous. We therefore distinguish a uniform satellite reference task from high-confidence independent-observation evaluation. Agreement across these layers is required before making claims about physical rainfall rather than agreement with one retrieval algorithm.

Mixture-of-experts models offer a natural representation of heterogeneous processes, but expert diversity alone is not a sufficient scientific contribution. Graph mixtures can route information over different structures or spatial ranges [6–8], and missing-modality mixtures can adapt to incomplete inputs [9]. If a router is trained only to minimize forecast loss, however, it may select experts using unstable regional cues. An apparently interpretable routing map can still reflect season, continent or sensor identity rather than physical transport or convective development. Attention weights or expert usage plots are not evidence that the router has learned a mechanism.

We address this problem through mechanism-constrained routing. MCR-Precip contains four propagation experts representing advection, local convective generation, orographic enhancement and persistence–decay. The router receives observable mechanism states—storm motion, wind and moisture transport, convective instability, terrain alignment, season, forecast horizon and data availability—but never region identity or the future target. Soft applicability priors encourage physically plausible expert use without hard-coding the answer. Counterfactual perturbations then make the interpretation falsifiable: rotating transport, weakening instability, masking terrain or removing a sensor should change expert weights and predictions in specified directions. Selective prediction provides a second safety mechanism by allowing the system to abstain when evidence is insufficient.

The study is designed around two distinct data tracks. The Historical Common-Core track uses globally consistent half-hourly precipitation, forecast-origin-safe dynamic fields and static terrain from 2001–2024. It supports temporal evaluation and leave-one-region-out transfer. The MAZU-Rich track uses the single global year available in 2025, including FYMERG and additional atmospheric variables, to study self-supervised pretraining, modality gain and sensor shift. MAZU does not define the long-term extreme climatology and cannot independently demonstrate cross-year generalization.

We test three hypotheses. First, mechanism-constrained routing should transfer more consistently than unconstrained dense or mixture models when an entire dryland region is held out. Second, counterfactual regularization should reduce routing responses that contradict observable transport, instability and terrain states. Third, data-availability-aware selection should provide a better risk–coverage trade-off than mandatory prediction under missing sensors. The intended contribution is therefore not another collection of expert branches, but an empirical test of whether physically falsifiable routing improves reliable prediction under geographic and observational shift.

## Results

### A global dryland benchmark exposes distinct shifts

We construct the Dryland Extreme Precipitation Benchmark (DEPB) over four macro-regions: the Arabian Peninsula, southwestern North America, interior Australia and southern Africa. A common aridity mask retains hyper-arid, arid and semi-arid cells. Half-hourly precipitation is harmonized to a common 0.1° grid, and each forecast sample contains the preceding six hours of observations. Targets are accumulated rainfall and exceedance occurrence over the following 1, 3 and 6 hours.

An extreme is defined by both a local monthly wet-period percentile and an absolute floor. The primary thresholds are the local P99.9 with floors of 10 mm h−1, 20 mm 3 h−1 and 30 mm 6 h−1. This combined definition prevents a climatologically rare but physically weak drizzle event from being treated as equivalent to damaging rainfall. Connected exceedance cells are grouped into event objects, and all samples associated with one meteorological event remain in the same split.

The completed benchmark contains TODO-RESULT-DATA-01 half-hourly scenes, TODO-RESULT-DATA-02 independent events and TODO-RESULT-DATA-03 high-confidence station or radar matches. Regional event frequency differs by TODO-RESULT-DATA-04, while sensor availability differs by TODO-RESULT-DATA-05. Figure 1 will show that differences are not limited to base rate: storm speed, convective growth, terrain alignment and retrieval uncertainty occupy different joint distributions across regions. The Jensen–Shannon or energy-distance shift between each region pair is TODO-RESULT-DATA-06.

Satellite–station agreement must be reported before any model comparison. At quality-controlled gauges, the common satellite reference achieves TODO-RESULT-OBS-01 for 1-hour occurrence and TODO-RESULT-OBS-02 for 3-hour accumulation. The errors stratified by intensity, terrain and microwave-observation age are TODO-RESULT-OBS-03. We will use these results to define the high-confidence evaluation subset; regions that fail the preregistered observation audit will not support physical rainfall claims.

### Conventional models lose reliability across regions

We compare climatology, persistence, optical-flow extrapolation, gradient-boosted trees, recurrent convolutional models, encoder–decoder models, graph networks and an unconstrained dense mixture. In region-matched temporal testing, the best conventional baseline is TODO-RESULT-BASELINE-01. Its PR-AUC, CSI and Brier Skill are TODO-RESULT-BASELINE-02, TODO-RESULT-BASELINE-03 and TODO-RESULT-BASELINE-04 at 1 hour, with corresponding values at 3 and 6 hours reported in Supplementary Table 3.

Holding out an entire continent-scale region changes this ranking by TODO-RESULT-OOD-01. The average relative PR-AUC reduction is TODO-RESULT-OOD-02, and the worst-region calibration error changes by TODO-RESULT-OOD-03. Figure 2 will distinguish three failure modes: displacement of a persistent rain object, missed local convective growth, and excessive spatial smoothing of a rare core. These modes motivate the expert definitions; they must be established independently of MCR-Precip rather than inferred from its routing weights.

The analysis will also test whether apparent geographic degradation is merely a consequence of different event prevalence. After prevalence-matched subsampling and threshold-standardized evaluation, the residual cross-region gap is TODO-RESULT-OOD-04. A hierarchical regression over event intensity, season, terrain and observation quality attributes TODO-RESULT-OOD-05 of the remaining variation to mechanism-state shift. If this result is absent, the manuscript will not claim that a new routing mechanism is needed.

### Mechanism-constrained routing improves transfer

MCR-Precip combines predictions from four experts using a sparse router constrained by mechanism-applicability priors. In leave-one-region-out evaluation, it changes mean PR-AUC relative to the strongest matched-compute baseline by TODO-RESULT-MCR-01, CSI by TODO-RESULT-MCR-02 and Brier Skill by TODO-RESULT-MCR-03. Event-block bootstrap intervals are TODO-RESULT-MCR-04. Region-specific effects are TODO-RESULT-MCR-05; the main cross-regional claim requires effects in the same direction in at least three of four held-out regions and no material degradation of the worst-region calibration.

The gain must not be explained by parameter count. A dense model with matched parameters and floating-point operations produces TODO-RESULT-MATCHED-01, while an unconstrained mixture with the same experts produces TODO-RESULT-MATCHED-02. Removing the applicability prior changes TODO-RESULT-ABLATION-01; removing counterfactual regularization changes TODO-RESULT-ABLATION-02; and replacing the orographic expert with another generic convolutional expert changes TODO-RESULT-ABLATION-03. Expert-count and capacity controls are reported in Supplementary Figure 5.

We separately evaluate two uses of global 2025 MAZU data. In strict zero-shot experiments, all samples from the held-out region are excluded from pretraining and adaptation. In label-free transductive experiments, self-supervised pretraining may observe inputs from the held-out region but not rainfall targets. The former changes TODO-RESULT-MAZU-01 and the latter changes TODO-RESULT-MAZU-02. Results from the transductive protocol will never be described as geographically blind. Because MAZU covers only one year, neither protocol is used to estimate local P99.9 climatology or claim interannual robustness.

### Tail skill and calibration remain coupled

Rare-event ranking is insufficient if issued probabilities are unreliable. We therefore evaluate threshold-specific Brier Skill, negative log-likelihood, reliability diagrams and event-level precision–recall. Calibration is fitted on source-region validation years only. No target-region labels are used to calibrate leave-one-region-out forecasts.

At 1, 3 and 6 hours, MCR-Precip has expected calibration errors of TODO-RESULT-CAL-01, TODO-RESULT-CAL-02 and TODO-RESULT-CAL-03. Reliability at probabilities above 0.5 is TODO-RESULT-CAL-04. Spatial pooling at 10, 25 and 50 km changes the comparative ranking by TODO-RESULT-SPATIAL-01, revealing TODO-RESULT-SPATIAL-02 about displacement versus intensity error. Object-based evaluation attributes TODO-RESULT-SPATIAL-03 of missed events to initiation, propagation or duration errors.

We will report both the uniform satellite-reference task and the independent-observation subset. On gauges and radar–gauge products, MCR-Precip changes TODO-RESULT-INDEPENDENT-01 relative to the strongest baseline. A discrepancy between satellite-reference and independent-observation rankings will be treated as retrieval dependence, not hidden in an aggregate score. If the improvement does not reproduce on independent observations, the abstract and title must be weakened accordingly.

### Selective prediction controls degradation under missing sensors

Dryland observations are not missing at random. Satellite overpass timing, retrieval quality and local station coverage correlate with storm type and geography. MCR-Precip therefore receives explicit data-availability masks and outputs an uncertainty score used for abstention. We simulate realistic missingness by masking full sensor channels, contiguous time blocks and region-specific availability patterns; arbitrary independent pixel dropout is reported only as a diagnostic.

At matched coverage of TODO-RESULT-COVERAGE-01, selective MCR-Precip changes event error by TODO-RESULT-SELECTIVE-01 and calibration error by TODO-RESULT-SELECTIVE-02 relative to mandatory prediction. Compared with entropy-based rejection from the dense model and uncertainty from the unconstrained mixture, its area under the risk–coverage curve is TODO-RESULT-SELECTIVE-03. Conditional coverage across regions and event intensities is TODO-RESULT-SELECTIVE-04. The method will be described as reliable only if abstention does not systematically discard the most intense events or one geographic region.

The missing-modality ablation tests whether routing responds to physical information rather than a fixed sensor hierarchy. Removing recent precipitation should shift weight toward TODO-RESULT-MISSING-01; removing dynamic atmospheric fields should produce TODO-RESULT-MISSING-02; and removing terrain should produce TODO-RESULT-MISSING-03. Any performance retained through correlations with region or season will be exposed by the geographic OOD split.

### Counterfactuals make routing interpretations falsifiable

We evaluate controlled perturbations that preserve unrelated inputs. Rotating horizontal transport by 90° should rotate or reduce the advection expert's downstream influence; reducing CAPE and precipitable water should reduce the local-generation contribution; flattening terrain should reduce the orographic contribution; and removing recent rainfall should change persistence and uncertainty. Counterfactual targets are directional constraints, not synthetic rainfall truth.

The unconstrained mixture violates these directional expectations in TODO-RESULT-CF-01 of eligible cases, compared with TODO-RESULT-CF-02 for MCR-Precip. Router sensitivity to transport rotation is TODO-RESULT-CF-03, to instability reduction TODO-RESULT-CF-04, and to terrain masking TODO-RESULT-CF-05. The relationship between reduced violation and OOD skill is TODO-RESULT-CF-06. These analyses will support a mechanism claim only if changes occur in physically eligible cases and are absent in matched negative controls.

Failure cases remain necessary. Figure 6 will include at least one displaced organized storm, one unobserved convective initiation, one terrain-associated false alarm and one sensor-conflict case. Their errors are TODO-RESULT-FAIL-01. We will distinguish failures of the common reference product, input availability, model routing and the event definition. No case will be selected solely because it favors MCR-Precip.

## Discussion

This study is designed to test whether mechanism constraints can improve the reliability of short-duration extreme-rainfall prediction across drylands. Its central comparison is not between a large neural network and a small baseline, but between routing strategies with matched experts and computational capacity. A positive result would indicate that observable transport, instability and terrain states provide a more transferable basis for conditional computation than unconstrained loss-driven routing. A negative result would be equally informative: it would show that the proposed mechanistic decomposition does not add value beyond strong spatiotemporal baselines under the selected resolution and observations.

The work deliberately separates globally uniform reference labels from independent physical observations. IMERG enables consistent training and evaluation across continents, but agreement with IMERG can reflect retrieval-specific structure. Gauge and radar–gauge subsets are therefore decision gates for the strength of the final claim. This distinction is particularly important in drylands, where intermittent microwave sampling, evaporation below cloud base and sparse gauges may produce intensity-dependent errors. A model that predicts the satellite product well but fails against independent measurements cannot be presented as a more accurate rainfall predictor.

Mechanism constraints do not make the network a numerical weather model. The applicability priors are partial, noisy statements about when an expert should be useful, and the counterfactuals test directional behavior rather than conservation laws. Their value lies in making routing interpretations falsifiable. They can reveal when a router continues to use an advection expert after transport is removed or an orographic expert after terrain information is masked. This is stronger than displaying attention maps, but it does not establish that the internal representation is a complete physical mechanism.

Selective prediction addresses another practical limitation. A system deployed across drylands will encounter sensor outages and observation patterns that differ from training. Reporting a probability for every sample can conceal catastrophic failure. Risk–coverage analysis instead asks whether the model can reduce error by withholding a defined fraction of predictions, and whether that withholding is equitable across region and event intensity. This is a research evaluation, not an operational warning policy; agencies would still need to define the consequences and fallback actions associated with abstention.

Several limitations will remain. First, a 0.1° satellite reference cannot resolve all convective cores or local terrain effects. Second, local percentile thresholds depend on a sufficiently stable observation record and do not imply equal impacts across regions. Third, archived analysis fields may not have been available at forecast origin; only explicitly archived forecast or reforecast fields can support operational claims. Fourth, one year of MAZU data provides spatial diversity but not interannual climatology. Finally, the four expert categories simplify interactions among cold pools, mesoscale organization, moisture convergence and complex terrain.

The manuscript will retain the title's claim of reliable cross-dryland prediction only if four preregistered conditions are met: improvements are directionally consistent in at least three held-out regions; event-block confidence intervals support the main comparison; worst-region calibration does not deteriorate; and independent observations reproduce the principal conclusion. Otherwise the paper will be reframed as a benchmark, an analysis of failure under shift, or an application study. Wadi flood risk may be explored downstream by combining rainfall forecasts with hydrology, but no flood occurrence or impact claim follows from precipitation prediction alone.

## Methods

### Study regions and dryland mask

The four macro-regions are Arabian Peninsula (12–32° N, 34–60° E), southwestern North America (20–40° N, 120–100° W), interior Australia (35–15° S, 120–145° E), and southern Africa (35–15° S, 10–35° E). Within each box, cells are retained when the selected version of the Global Aridity Index classifies them as hyper-arid, arid or semi-arid (aridity index below 0.65). Coastal ocean cells and cells without a stable precipitation record are removed. Exact source versions and mask checksums will be frozen before event extraction.

### Data tracks

Historical Common-Core covers 2001–2024. The minimum causal input is six hours of half-hourly precipitation preceding forecast origin plus static elevation, slope, aspect and land–sea mask. Dynamic atmospheric fields are included only where an archived forecast or reforecast has initialization time no later than forecast origin. ERA5 and ERA5-Land support climatology, mechanism diagnostics and explicitly labelled retrospective analyses; they are not silently substituted for operational inputs.

MAZU-Rich covers 2025. It harmonizes global MAZU variables, FYMERG precipitation where available, atmospheric indicators and the common static fields. It supports masked self-supervised pretraining, modality ablation and prospective schema testing. Strict geographic OOD pretraining excludes the held-out macro-region. A separate transductive protocol may use unlabeled held-out inputs and is labelled accordingly.

### Reference precipitation and observation audit

IMERG Final half-hourly precipitation provides the uniform reference target. The pipeline retains calibrated precipitation, quality information, microwave observation timing and source version. Gauge observations are filtered using provider quality flags, accumulation duration, station continuity, duplicates, location history and physical-range checks. Radar–gauge mosaics are evaluated in their native quality domain before resampling. FYMERG is treated as a second retrieval product, not a gauge substitute.

For each region, at least 20 candidate extremes are manually audited during Gate 0. A region is eligible for the strongest physical-rainfall claims only if at least TODO-RESULT-MIN-INDEPENDENT independent event matches pass the preregistered timing and distance tolerances and if observation completeness exceeds TODO-RESULT-MIN-COMPLETENESS. These thresholds will be finalized before model training and recorded in the dataset card.

### Extreme-event construction

For each cell, month and horizon, the percentile threshold is estimated from wet periods in the designated 2001–2018 climatology window. A wet period has positive accumulation above the product's reliable detection floor. The final threshold is the maximum of the P99.9 estimate and the absolute floor: 10 mm for 1 hour, 20 mm for 3 hours and 30 mm for 6 hours. Sensitivity analyses use P99, P99.5 and P99.9 and alternative absolute floors.

Eight-neighbour connected exceedance cells are linked through time when their footprints overlap after a one-cell spatial dilation or when motion-consistent matching connects them. Objects separated by more than one target interval are distinct events. Samples sharing an event, including precursor contexts and overlapping target windows, receive one immutable `event_group_id`.

### Splits and leakage control

The temporal split uses 2001–2021 for training, 2022–2023 for validation and 2024 as a frozen temporal test. Leave-one-region-out experiments hold out one macro-region from all supervised training and validation. Source-region validation data select hyperparameters, calibrators, thresholds and abstention rules. The held-out target is evaluated once per frozen experiment version.

Climatological thresholds define the target and may use the fixed pre-2019 reference window in a held-out region; target-region predictors or labels are not used for model fitting. Normalization statistics, missing-value imputers and learned preprocessing use source training data only. A leakage audit rejects samples with input `availability_time` later than `forecast_origin`, duplicated event groups across splits, or overlapping target data used in self-supervised objectives.

### MCR-Precip architecture

Let `x` denote the common encoded context, `q` observable mechanism state, `m` availability mask, and `l` forecast horizon. Four experts produce latent forecasts: advection `E_adv`, local convective generation `E_conv`, orographic enhancement `E_oro`, and persistence–decay `E_per`. The router produces non-negative weights summing to one:

`alpha = softmax(R(q, m, l) / tau)`.

The combined latent state is `z = sum_k alpha_k E_k(x, m, l)`. Separate heads output exceedance probability, precipitation quantiles and predictive uncertainty. Region identity, latitude–longitude tokens that uniquely identify a region, and future observations are excluded from router inputs. Coordinate information required for geometry is represented relative to each crop and audited for region leakage.

The advection expert warps latent features using forecast-origin-safe horizontal transport and observed storm motion. The convective expert preserves local maxima and represents growth using instability and moisture features. The orographic expert propagates along terrain-relative flow and slope features. The persistence expert models continuation and decay from recent precipitation without directional transport. Implementation details and matched-capacity rules are specified in the Supplementary Methods.

### Mechanism priors and counterfactual loss

Applicability scores `pi_k(q)` are noisy soft priors, not labels. Strong coherent transport increases `pi_adv`; instability and moisture convergence increase `pi_conv`; moist upslope flow increases `pi_oro`; and recent coherent rainfall with weak forcing increases `pi_per`. The routing prior loss is `L_prior = KL(stopgrad(pi) || alpha)` only for samples where the corresponding mechanism variables pass quality checks. Its weight is selected on source validation data.

Counterfactual transformations include a 90° rotation of horizontal transport, reduction of CAPE and precipitable water, flattening of terrain-derived channels and masking of recent precipitation. Each transformation has an eligibility rule and a directional routing constraint. The counterfactual loss penalizes violations without prescribing a synthetic rainfall target. Matched negative controls perturb variables that should not affect the selected expert over the same sample.

### Objectives and optimization

The total objective is `L = L_occ + lambda_q L_quantile + lambda_p L_prior + lambda_cf L_counterfactual + lambda_sel L_selective`. `L_occ` is a class-balanced proper scoring loss for exceedance probability; primary reporting uses Brier and log losses even if a tail-weighted surrogate is used for optimization. `L_quantile` predicts registered rainfall quantiles. `L_selective` trains or validates an uncertainty score without using test errors.

Optimization schedules, model dimensions, random seeds, stopping rules and compute budgets will be frozen in configuration files. Each deep model is trained with at least TODO-RESULT-SEEDS independent seeds. Parameter count, floating-point operations, training energy proxy, inference memory and latency are reported.

### Baselines and ablations

Baselines are monthly climatology, Eulerian persistence, optical-flow extrapolation, HGB/XGBoost, ConvLSTM, a U-Net-like encoder–decoder, a graph neural network, a dense matched-capacity model, and an unconstrained mixture using identical experts. Where a named implementation cannot be reproduced under the common input contract, the deviation is recorded rather than silently changing its information set.

Ablations remove mechanism priors, counterfactual regularization, orographic specialization, extreme-preserving operations, missingness masks and MAZU pretraining. Expert counts of two, four and eight and matched-parameter dense controls test whether gains reflect conditional computation or capacity.

### Calibration and selective prediction

Probability calibration is fitted separately for each horizon using source-region validation data. The primary calibrator is selected before target evaluation from temperature, beta or isotonic calibration according to validation Brier score and reliability. Target-region recalibration is prohibited in zero-shot experiments.

Uncertainty combines predictive distribution spread and ensemble disagreement. Abstention thresholds are fixed on source validation data. Risk–coverage curves report event error, Brier score and false-alarm ratio as coverage decreases. Coverage is stratified by region, intensity and missingness pattern to reveal selective failure.

### Evaluation and statistical analysis

Primary discrimination metrics are PR-AUC and CSI; POD, FAR and ROC-AUC are secondary. Probabilistic metrics are Brier Score, Brier Skill, negative log-likelihood and reliability. Spatial verification uses neighbourhood radii of 10, 25 and 50 km and object-based location, area, duration and intensity errors. All choices are fixed before opening the target-region result bundle.

Confidence intervals and paired model differences use bootstrap resampling of independent `event_group_id` blocks, with TODO-RESULT-BOOTSTRAP replicates. The main method claim requires directional improvement in at least three held-out regions, a 95% interval excluding zero for the pooled event-level comparison, and no material deterioration of worst-region calibration. Multiple secondary comparisons use a declared false-discovery-rate procedure.

### Reproducibility and prospective evaluation

Every result is generated from an immutable experiment manifest containing source versions, checksums, split identifiers, configuration, code commit, environment lock, model artifacts and random seeds. Figures and tables read machine-readable result files; values are not copied manually into plotting scripts.

From project initiation onward, operational satellite products, international forecasts and weather-foundation-model outputs will be archived with initialization, availability and valid times. After the model and policy are frozen, the 2026–2027 prospective set will be evaluated once. Prospective results will not be used to tune the submitted model.

## Data availability

No new cross-regional benchmark is released with this draft. The final study will deposit harmonized manifests, event identifiers, frozen splits, quality masks and derived features in TODO-DATA-REPOSITORY under TODO-LICENSE, subject to upstream licences. Public source data will be referenced rather than redistributed where required. Restricted station or forecast archives will be accompanied by access instructions and a reproducible public-data subset. Numerical source data underlying every figure and table will be released with the accepted manuscript.

## Code availability

The current repository contains Saudi-region extraction and indicator prototypes but not the completed MCR-Precip experiment pipeline. Before submission, code central to the claims will be archived at TODO-CODE-REPOSITORY with DOI TODO-CODE-DOI. The release will include environment locks, data manifests, preprocessing, leakage audits, baselines, model training, calibration, evaluation and figure-generation commands. A private reproducible snapshot will be made available to editors and reviewers at submission.

## References

The working bibliography is maintained in [references.bib](references.bib). Citation numbering will be generated when the manuscript is converted to Word or LaTeX. Every reference used in the submitted draft must be verified against the publisher or official dataset record.

## Acknowledgements

TODO-ACKNOWLEDGEMENTS-01

## Author contributions

TODO-AUTHOR-CONTRIBUTIONS-01. Contributions will be recorded using the CRediT taxonomy after the author list and responsibilities are finalized.

## Competing interests

The authors declare TODO-COMPETING-INTERESTS-01.

## Figure legends

**Figure 1 | Benchmark design and dryland distribution shifts.** a, Four study regions and dryland mask. b, Historical Common-Core and MAZU-Rich data tracks. c, Event frequency and observation availability. d, Joint distributions of transport, instability, terrain alignment and retrieval quality. All counts and summary values will be populated from frozen dataset audit artifacts.

**Figure 2 | Conventional models fail differently under geographic shift.** a, Temporal versus leave-one-region-out PR-AUC. b, Change in Brier Skill and reliability. c–e, representative displacement, initiation and smoothing failures selected using preregistered criteria.

**Figure 3 | MCR-Precip architecture and cross-regional performance.** a, Four experts, mechanism router and output heads. b, Applicability-prior and counterfactual constraints. c, Event-level paired differences against matched-compute baselines. d, Region–horizon matrix with bootstrap intervals.

**Figure 4 | Tail probability and spatial verification.** a, Precision–recall curves. b, Reliability diagrams. c, Brier Skill by intensity. d, Neighbourhood and object-based scores by spatial tolerance.

**Figure 5 | Missing sensors and selective prediction.** a, Realistic missingness scenarios. b, Risk–coverage curves. c, Conditional coverage by region and intensity. d, Router and uncertainty responses to removed modalities.

**Figure 6 | Counterfactual routing and failure cases.** a, Directional router violation rates. b, Transport rotation. c, instability reduction. d, terrain masking. e–h, preregistered failure examples including observation conflict.
