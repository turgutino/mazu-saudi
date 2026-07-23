# Cross-scale atmospheric regimes govern sub-daily rainfall extremes across global drylands

**Article type:** Article
**Target journal:** Nature Communications or comparable Earth-system journal
**Draft status:** Results-ready scientific manuscript; not submission-ready
**Authors:** TODO-AUTHOR-AI4S-01
**Affiliations:** TODO-AFFILIATION-AI4S-01
**Correspondence:** TODO-CORRESPONDENCE-AI4S-01

> **Scientific-integrity notice.** The regime atlas, physical associations and forecast-error results described below have not yet been computed. Every unknown empirical statement is marked `TODO-RESULT-AI4S-*`. Representation learning, clustering and explainability are discovery tools; they do not by themselves establish a physical mechanism or causality.

## Abstract

Sub-daily rainfall extremes in drylands emerge from interactions between large-scale circulation, moisture transport, convective instability and local terrain, yet it remains unclear which combinations recur across continents and which are systematically missed by forecasts. We assemble a 2001–2024 event catalogue spanning the Arabian Peninsula, southwestern North America, interior Australia and southern Africa. Using representation learning as a discovery instrument, followed by consensus clustering and independent dynamical diagnostics, we identify TODO-RESULT-AI4S-ABSTRACT-01 reproducible cross-scale regimes. These regimes explain TODO-RESULT-AI4S-ABSTRACT-02 of event-to-event variation in rainfall morphology and TODO-RESULT-AI4S-ABSTRACT-03 of short-range forecast error beyond region, season, intensity and observation quality. Matched-event analysis indicates that TODO-RESULT-AI4S-ABSTRACT-04 differentiates local intensification under similar large-scale forcing. The least predictable regime exhibits TODO-RESULT-AI4S-ABSTRACT-05 and is independently recovered in the 2025 MAZU-rich record. These results would reveal how large-scale atmospheric preparation is converted into local rainfall extremes and establish a mechanism-based account of forecast blind spots across global drylands.

## Introduction

Drylands receive a large fraction of their annual rainfall from a small number of events. The same events can produce water resources and severe disruption, while their short duration and limited spatial footprint make them difficult to observe and predict. At the daily scale, extreme precipitation in many arid regions is strongly associated with large-scale dynamical forcing, including Rossby-wave breaking that transports moisture and promotes ascent [1]. At hourly scales, convection, circulation and topography jointly shape rainfall intensification and its departure from simple thermodynamic scaling [2,3]. What remains unresolved is the cross-scale conversion problem: why do apparently similar large-scale environments sometimes produce a localized sub-daily extreme and sometimes fail to do so?

This question cannot be answered by cataloguing one driver at a time. Extreme events may share upper-tropospheric forcing but differ in low-level moisture convergence, convective inhibition, terrain alignment, organization or storm propagation. Conversely, events with similar rainfall morphology may arise from different combinations of large- and local-scale processes. Regional case studies provide detailed mechanisms, but their categories are not necessarily transferable. A global analysis based only on daily accumulations can conceal the initiation, growth and displacement of the short-lived rain cores most relevant to local impacts.

Artificial intelligence can help organize this high-dimensional event space. Self-supervised representations can reduce multivariate fields to recurring event states; clustering can propose candidate regimes; and nonlinear models can test whether combinations of drivers explain more variation than isolated indices. AI does not remove the need for atmospheric reasoning. A cluster can reflect continent, season, observing system or preprocessing rather than physics. Feature attribution describes model sensitivity rather than causal influence. Scientific use therefore requires a strict separation between regime discovery and independent validation, tests of stability across data products and algorithms, and negative controls that could falsify the interpretation [4,5].

The distinction between prediction and discovery is also important. Modern machine-learning weather models can produce highly skilful global forecasts [6,7], but aggregate scores do not reveal why errors concentrate in particular events. Conversely, a mechanism atlas is scientifically useful even if it does not immediately yield a new forecasting architecture. By conditioning forecast errors on physically validated event regimes, we can ask whether models fail because of intensity, displacement, convective initiation, terrain coupling or an unresolved transition between synoptic preparation and local growth.

Here we use AI as an event-discovery instrument rather than as the principal contribution. We first identify sub-daily extreme-rainfall objects from a globally consistent satellite record. We then learn representations of their pre-onset large-scale environment and rainfall evolution without using region labels or forecast errors. Consensus clustering proposes candidate regimes. The regimes are accepted only if they remain stable under resampling, reproduce in a held-out continent and year block, and exhibit coherent signals in diagnostics withheld from discovery, including Rossby-wave-breaking catalogues, moisture budgets, vertical motion and independent precipitation observations.

We address three questions. First, does a small set of cross-scale regimes recur across physically distinct drylands? Second, under similar large-scale forcing, which local conditions are associated with conversion into short-duration extreme rainfall? Third, do these regimes explain forecast error beyond geography, season, event intensity and observing-system quality? The intended result is a falsifiable account of dryland extreme-rainfall organization and forecast blind spots, not a claim that a latent-space visualization is itself atmospheric discovery.

## Results

### A multi-source catalogue resolves sub-daily dryland extremes

We identify independent 1-, 3- and 6-hour extreme-rainfall objects between 2001 and 2024 over the Arabian Peninsula, southwestern North America, interior Australia and southern Africa. The event definition combines local monthly percentiles with absolute intensity floors, while object tracking prevents neighbouring grid cells and overlapping windows from being treated as independent events. Each object includes a 48-hour pre-onset environment, its sub-daily rainfall life cycle, observation-quality state and links to independent gauges or radar where available.

The final catalogue contains TODO-RESULT-AI4S-DATA-01 events, of which TODO-RESULT-AI4S-DATA-02 have high-confidence independent precipitation support. Event frequency, duration and footprint differ among regions by TODO-RESULT-AI4S-DATA-03. Agreement between the uniform satellite reference and independent observations is TODO-RESULT-AI4S-DATA-04 and varies with intensity, terrain and sampling age by TODO-RESULT-AI4S-DATA-05. These uncertainties are carried into all regime estimates instead of treating every retrieved pixel as equally certain.

Figure 1 will show that daily accumulation obscures distinct sub-daily evolution. Events with comparable daily totals have TODO-RESULT-AI4S-MORPH-01 differences in initiation rate, motion, maximum core intensity and object lifetime. This establishes the temporal-scale gap that motivates the analysis. If event morphologies do not remain distinguishable after observation-quality matching, the cross-scale discovery claim will be stopped.

### AI identifies recurrent regimes rather than geographic clusters

An event representation is learned from standardized pre-onset atmospheric anomalies and rainfall-object evolution. Region identity, forecast errors, impacts and post-event reanalysis are excluded. Candidate partitions from linear, nonlinear and graph-based representations are combined through consensus clustering. Cluster number is chosen by preregistered stability and reproducibility criteria, not by its ability to maximize forecast-error differences.

The accepted atlas contains TODO-RESULT-AI4S-REGIME-01 regimes. Their bootstrap assignment stability is TODO-RESULT-AI4S-REGIME-02, and agreement across representation families is TODO-RESULT-AI4S-REGIME-03. A classifier trained to recover continent from the normalized representation obtains TODO-RESULT-AI4S-LEAK-01, compared with TODO-RESULT-AI4S-LEAK-02 before leakage controls. Each accepted regime appears in TODO-RESULT-AI4S-REGIME-04 continents and is recovered in leave-one-continent-out projection with adjusted mutual information TODO-RESULT-AI4S-REGIME-05.

The regimes are provisionally described by their physical signatures only after independent diagnostics. Expected candidates include synoptically forced moisture intrusion, dynamically organized propagation, terrain-locked enhancement and local thermodynamic initiation, but these names will not be imposed before analysis. Figure 2 will report objective composites, within-regime variability and ambiguous events rather than selecting a single visually ideal example.

### Independent diagnostics support cross-scale physical interpretations

To test whether the data-driven regimes correspond to atmospheric organization, we evaluate diagnostics withheld from representation learning. These include objective Rossby-wave-breaking and potential-vorticity features, vertically integrated moisture-flux convergence, pressure-velocity profiles, instability release, upslope moisture transport and, where feasible, Lagrangian moisture-source estimates. Regime interpretation requires multiple independent diagnostics with coherent timing.

The occurrence of objectively diagnosed wave breaking differs among regimes by TODO-RESULT-AI4S-PHYS-01. Moisture-flux convergence and dynamically forced ascent differ by TODO-RESULT-AI4S-PHYS-02 and TODO-RESULT-AI4S-PHYS-03, while terrain-relative transport differs by TODO-RESULT-AI4S-PHYS-04. These results must go beyond the already established daily-scale association between Rossby-wave breaking and arid-region precipitation: the new evidence must identify how sub-daily morphology or local amplification differs within a shared large-scale category.

Physical-budget closure is TODO-RESULT-AI4S-BUDGET-01 after accounting for data resolution and residual terms. Regime contrasts reproduce across alternative precipitation products and reanalysis choices with TODO-RESULT-AI4S-ROBUST-01 agreement. If a regime exists only in one retrieval or disappears when one diagnostic is withheld, it will be described as data-dependent rather than physical.

### Local conditions distinguish intensification under similar forcing

We construct matched event and non-event sets to isolate the conversion from atmospheric preparation to local extreme rainfall. Events are matched on season, region, large-scale potential-vorticity configuration, integrated moisture transport and synoptic ascent. Within these matched sets, we compare pre-onset low-level convergence, convective inhibition, terrain alignment, soil state where reliable, and recent convective organization. Matching quality and overlap are reported before outcome comparisons.

Under similar large-scale forcing, local extreme intensification is associated with TODO-RESULT-AI4S-LOCAL-01. The matched difference in peak 1-hour rainfall is TODO-RESULT-AI4S-LOCAL-02, and the probability of crossing the extreme threshold changes by TODO-RESULT-AI4S-LOCAL-03. Negative-control variables and lag-reversed tests produce TODO-RESULT-AI4S-NEGCTRL-01. Sensitivity to unmeasured confounding is TODO-RESULT-AI4S-CONFOUND-01.

These analyses identify conditional associations, not definitive causal effects. Stronger causal wording will be used only if natural experiments, intervention-like forecast perturbations or process-model experiments become available. Figure 3 will explicitly separate robust matched associations from exploratory pathways.

### Mechanism regimes reveal systematic forecast blind spots

Historical forecast or reforecast precipitation is matched to the event catalogue using initialization and valid times. Error is decomposed into missed initiation, displacement, intensity, area and duration. The analysis includes only fields available at forecast origin and compares models on a common verification support.

Forecast skill varies among regimes by TODO-RESULT-AI4S-ERROR-01. The least skilful regime has TODO-RESULT-AI4S-ERROR-02 characteristics and contributes TODO-RESULT-AI4S-ERROR-03 of all high-confidence misses. In a hierarchical model controlling for region, season, intensity, event size, lead time and observation quality, regime identity explains TODO-RESULT-AI4S-ERROR-04 of residual error, compared with TODO-RESULT-AI4S-ERROR-05 for geography alone.

Ensemble spread–error consistency and conditional entropy indicate an empirical predictability gap of TODO-RESULT-AI4S-PREDICT-01 in the transition-dominated regime. This is not called a fundamental predictability limit: it is the residual uncertainty under the observed information and forecast systems. Figure 4 will test whether model families share the same blind spot or whether specific representations reduce it.

### The atlas transfers across time, continents and sensors

Regime prototypes are frozen using the discovery period. We then evaluate 2019–2024 temporal confirmation, leave-one-continent-out recovery and the independent 2025 MAZU-rich record. MAZU is not used to estimate multi-year regime frequency. Its role is to test whether regime geometry and physical associations survive a new product family and observation pattern.

Prototype assignment in 2019–2024 has stability TODO-RESULT-AI4S-TIME-01. Held-out-continent events map to accepted regimes at rate TODO-RESULT-AI4S-OOD-01, with TODO-RESULT-AI4S-OOD-02 genuinely unresolved or novel events. In the 2025 MAZU-rich track, cross-product regime agreement is TODO-RESULT-AI4S-MAZU-01 and physical-signature agreement is TODO-RESULT-AI4S-MAZU-02. A high unassigned fraction will be treated as evidence that the atlas is incomplete, not forced into the nearest prototype.

## Discussion

The proposed analysis asks how large-scale atmospheric preparation becomes a localized, short-duration rainfall extreme. Its scientific value depends on identifying recurrent cross-scale organization that is not reducible to continent, season or one satellite retrieval. A successful result would connect three levels of evidence: stable data-driven event regimes, independent physical diagnostics, and regime-specific forecast errors. It would not claim that AI has discovered atmospheric laws from raw data without meteorological assumptions.

Daily-scale studies have already established the importance of Rossby-wave breaking in many arid regions [1]. Our intended advance is narrower and complementary. We seek to resolve diversity within and beyond that large-scale driver: whether moisture delivery produces propagating organization, terrain-locked enhancement, rapid local initiation or no sub-daily extreme, and how those outcomes relate to forecast performance. If the learned atlas merely reproduces an existing wave-breaking/non-wave-breaking split, the novelty claim will fail.

The study also reframes forecast evaluation. Country-level averages mix distinct physical problems, while event intensity alone may not explain why a model misses initiation or displaces a rain core. A mechanism-conditioned error atlas can show whether geographically distant events share a blind spot and whether apparently poor regional performance follows from a concentration of difficult regimes. Such evidence can guide observing strategies and model development without requiring a new forecasting network in this paper.

Several safeguards are essential. Discovery and validation variables are separated. Cluster number and representation are selected by stability rather than desired scientific effects. Region leakage is probed. Alternative algorithms and products must recover comparable regimes. Event-block resampling replaces pixel-level significance. Matched analyses disclose balance and unmeasured-confounding sensitivity. These safeguards reduce, but do not eliminate, the risk of turning a flexible latent representation into a post-hoc physical story.

Limitations will remain. IMERG is a retrieval product, and independent short-duration observations are sparse in many drylands. ERA5 may smooth convection and terrain, so its budgets cannot validate sub-grid processes directly. Objective wave-breaking and moisture diagnostics have definition uncertainty. Forecast archives change resolution and model generation over time. The four selected macro-regions do not represent every dryland. One year of MAZU provides an external sensor test but cannot establish long-term stability.

The strong title will be retained only if the atlas contains cross-continental regimes, independent diagnostics support their interpretation, local transition evidence survives matching and negative controls, and regime identity explains forecast error beyond obvious covariates. Otherwise the paper will be reframed as a benchmark of event diversity or a regional mechanism analysis. The manuscript makes no flood occurrence or impact claim; no rainfall mechanism will be presented as proof of either outcome.

## Methods

### Event catalogue and study domains

The study uses the same four dryland macro-regions and observation-state contract as the companion prediction project. Dryland cells are defined using a frozen aridity-index mask. IMERG Final provides the uniform half-hourly reference from 2001–2024; independent gauges, radar–gauge mosaics and FYMERG form validation layers. Extreme objects use local monthly P99.9 thresholds with absolute 1/3/6-hour floors and are grouped into independent meteorological events.

Each event contains a 48-hour pre-onset window, onset-to-decay rainfall objects and a 24-hour post-onset diagnostic window. Predictors, diagnostics and observations preserve source version, valid time, availability time, quality and checksum. Analysis fields are permitted for retrospective mechanism study but are never described as operationally available forecasts.

### Discovery and confirmation split

Events from 2001–2018 form the discovery set. Events from 2019–2024 provide frozen temporal confirmation. One macro-region is additionally withheld in each geographic recovery experiment. The 2025 MAZU-rich period is an external product/sensor confirmation set. Events linked to one weather system remain in one partition.

Hyperparameters for representation learning and consensus clustering are selected within discovery data using blocked resampling. Physical-diagnostic separation, accepted stability thresholds and the maximum number of candidate regimes are preregistered before opening confirmation results.

### Event representation

The discovery representation uses standardized anomalies of pre-onset large-scale circulation, moisture transport, instability, low-level flow, terrain-relative flow and observed precipitation evolution. It excludes region identifiers, forecast errors, impacts, objective regime labels reserved for validation and fields after the registered diagnostic cutoff.

At least one linear method, one established nonlinear/self-supervised encoder and one topology-preserving baseline are evaluated. Architecture novelty is not claimed. Crop geometry, temporal context and latent dimension are controlled across methods. A continent probe tests whether the representation is dominated by geography; additional analyses remove absolute coordinates and climatological means.

### Consensus regime discovery

Candidate partitions use k-means/Gaussian mixtures, spectral or density-based clustering as appropriate. Cluster counts from two to ten are examined. Bootstrap co-assignment, adjusted mutual information across algorithms, prototype separation, ambiguous-assignment rate and held-out reconstruction determine acceptance. Forecast error and withheld physical diagnostics cannot select cluster number.

An event receives `unassigned` status when its maximum prototype membership or consensus confidence is below a preregistered threshold. Rare regimes are retained only if they contain enough independent events and recur outside one region.

### Independent physical validation

Withheld diagnostics include potential-vorticity streamer/cutoff catalogues, Rossby-wave-breaking indicators, vertically integrated moisture-flux convergence, omega profiles, instability tendency, upslope transport and optional Lagrangian moisture sources. Composite anomalies use event-relative coordinates and timing. Field significance uses event-block resampling and false-discovery-rate control.

A regime receives a physical name only when at least two independent diagnostics, coherent temporal ordering and cross-region replication support it. Otherwise it retains a neutral identifier. Physical budgets report residuals and resolution limitations.

### Matched transition analysis

Treated events are local extreme intensifications; controls include non-intensifying precipitation objects or near-miss environments. Exact and propensity/distance matching balance region, month, synoptic PV configuration, IVT, large-scale ascent, antecedent precipitation and observation quality. Local variables of interest are withheld from the matching score when their association is being tested.

Balance, common support, alternative matching algorithms, lag-reversed outcomes, negative-control variables and sensitivity to unmeasured confounding are reported. Because the study is observational, results are described as conditional associations unless stronger identification becomes available.

### Forecast-error attribution

GEFS/TIGGE or other admissible historical forecasts are matched by initialization and lead. Precipitation verification uses the common reference and independent-observation subset. Object metrics separate initiation, displacement, peak intensity, area and duration errors. Hierarchical models include random effects for event/system and fixed effects for regime, region, season, intensity, lead, observation quality and forecast generation.

Regime explanatory value is evaluated by out-of-sample likelihood, partial deviance and variance partitioning against models without regime. Model-generation changes are stratified rather than pooled without adjustment. Ensemble spread, error and event-conditioned information measures quantify empirical forecastability without claiming a theoretical predictability limit.

### Robustness and uncertainty

All uncertainty uses independent event blocks. Regime stability is tested across seeds, algorithms, thresholds, precipitation products, reanalyses and region/year exclusions. Primary scientific claims require agreement in at least three macro-regions and replication in the temporal confirmation period. The 2025 MAZU track is reported separately.

### Reproducibility

Every event, representation, partition, diagnostic and statistical result is tied to a frozen manifest and code commit. Result text and figures are generated from machine-readable source artifacts. Exploratory analyses are labelled and cannot replace preregistered primary tests after confirmation data are opened.

## Data availability

No new global event atlas is released with this draft. The final catalogue, permitted harmonized fields, regime assignments, uncertainty, frozen splits and source-data tables will be deposited at TODO-DATA-AI4S-REPOSITORY under licences compatible with upstream products. Restricted observations will be accompanied by access instructions and a reproducible public subset.

## Code availability

The regime-discovery and physical-validation pipeline has not yet been implemented. Before submission, preprocessing, representation, consensus clustering, physical diagnostics, matching, forecast-error attribution and figure generation will be archived at TODO-CODE-AI4S-REPOSITORY with DOI TODO-CODE-AI4S-DOI and made available for editorial review.

## References

The working references are maintained in [references.bib](references.bib). All metadata and any `TODO-REFERENCE-*` entries must be resolved against primary records before submission.

## Acknowledgements

TODO-ACKNOWLEDGEMENTS-AI4S-01

## Author contributions

TODO-AUTHOR-CONTRIBUTIONS-AI4S-01. An atmospheric-dynamics collaborator should participate in hypothesis definition, diagnostic selection and interpretation rather than only reviewing the final text.

## Competing interests

The authors declare TODO-COMPETING-INTERESTS-AI4S-01.

## Figure legends

**Figure 1 | Sub-daily extreme-rainfall catalogue and temporal-scale gap.** Four dryland domains, event construction, observation support and examples demonstrating different sub-daily evolution under similar daily accumulation.

**Figure 2 | Stable cross-scale atmospheric regimes.** Consensus workflow, prototype stability, continent leakage controls, event-relative composites and ambiguous/unassigned events.

**Figure 3 | Independent physical validation and local transition evidence.** Withheld dynamical diagnostics, moisture and vertical-motion budgets, matched-event balance and local-condition contrasts.

**Figure 4 | Regime-conditioned forecast blind spots.** Forecast skill and decomposed object errors by regime, hierarchical variance partitioning, spread–error behaviour and cross-model agreement.

**Figure 5 | Transfer across continents, time and sensors.** Leave-one-continent recovery, 2019–2024 confirmation, 2025 MAZU-rich prototype assignment and unresolved events.
