# Historical Warning Research Assets

This directory contains the frozen scientific assets used by the MAZU Saudi
historical warning exercise. It is not an application and has no web entry
point.

The only current product is the React + FastAPI competition application
documented in [`APPLICATIONS.md`](../../APPLICATIONS.md).

## Contents

| Directory | Purpose |
|---|---|
| `agent/` | Verified inference tools, saved models, bounded-agent experiments and audit reports |
| `data/` | Local consolidated NetCDF dataset; ignored by Git |
| `kg/` | Versioned evidence graph, causal-evidence records and graph construction scripts |
| `model/` | Historical model, calibration, ensemble and verification experiments |
| `pipeline/` | Reproducible dataset consolidation and feature-enrichment scripts |
| `reports/` | Frozen bilingual report artifacts exposed by the competition backend |
| `verification/` | Reproduction instructions and verification scripts |

The former static HTML pages and their page generators were removed after
their useful content was incorporated into `competition_app/`. Their 33 image
assets were byte-identical to the copies now owned by
`competition_app/public/media/`, so only the product copies remain.

## Data locations

Scripts use repository-relative defaults and accept these overrides:

- `MAZU_HISTORICAL_RAW_DIR`: directory containing
  `saudi_indicators_*.nc`.
- `MAZU_HISTORICAL_DATA_DIR`: directory containing or receiving
  `mazu_dataset.nc`.

The competition backend reads the same assets through
`src/mazu_saudi/competition/adapters.py`; the React frontend never loads model
or NetCDF files directly.

## Scientific boundary

These assets support a retrospective 2025 `t → t+1` exercise based partly on
proxy labels. Recorded audit results establish traceability to the frozen
artifacts, not independent disaster truth, cross-year generalization, or
real-time operational readiness.
