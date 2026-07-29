# MAZU Saudi Historical Warning Console

## Product role

The competition application is an offline historical-warning exercise over the
project's frozen 2025 Saudi dataset. It is the primary product entrypoint and
keeps the former `warning_demo` pages as a read-only evidence archive.
The repository-wide lifecycle map is maintained in
[`APPLICATIONS.md`](../APPLICATIONS.md); the MCR research prototype is not a
second competition application.

The public application has five routes:

- `/console`: scenario presets, free city/date/hazard queries and the risk bulletin.
- `/analysis`: model field, rule field, ensemble spread, indicators and verification metrics.
- `/evidence`: event-specific mechanism, indicator and literature-evidence view.
- `/assistant`: deterministic analysis with optional DeepSeek wording.
- `/reports`: fixed reports plus generated HTML/PDF, JSON and CAP Exercise artifacts.

Every page states that this is a historical exercise, uses 2025 data and is not
an operational warning. Proxy labels are not described as independent disaster
truth.

## Local start

The `ml` conda environment must contain the project dependencies. From the
repository root:

```bash
./scripts/start_competition_app.sh
```

Open `http://127.0.0.1:8765`. The script builds the React application, runs the
data/model preflight and starts the FastAPI service. Set `MAZU_APP_PORT` to use a
different local port.

The default dataset is `warning_demo/data/mazu_dataset.nc`. To keep the dataset
elsewhere, set `WARNING_DEMO_DATA_DIR` to the directory containing
`mazu_dataset.nc`.

DeepSeek is optional:

```bash
DEEPSEEK_API_KEY=... ./scripts/start_competition_app.sh
```

Without the key, the assistant returns a deterministic analysis from the frozen
forecast, indicators and evidence. If the external request fails, it falls back
to the same deterministic path. The key is never returned to the browser or
stored in SQLite.

## Runtime data

Local state is written under `runtime/competition_app/`:

- `audit.sqlite3`: runs, assistant messages and artifact records.
- `artifacts/`: printable HTML, evidence JSON and CAP XML.

The runtime directory, the 311 MB dataset, frontend dependencies and build
output are not committed. Missing data or model artifacts place the application
in Archive Mode: reports and legacy pages remain available, while new
prediction runs are blocked.

## API boundary

The FastAPI contract is under `/api/v1` and exposes health/configuration,
scenarios, audited runs, three derived grid layers, event evidence, deterministic
or optional-LLM analysis, CAP Exercise and report artifacts.

The backend calls the existing verified tools in `warning_demo/agent/tools.py`.
The city result is therefore numerically identical to the legacy tool output.
The map field is evaluated directly from the same saved model, feature order,
stride and prior-day input date.

## Verification

```bash
npm --prefix competition_app test
npm --prefix competition_app run build
conda run -n ml python -m pytest -q tests
```

The tests cover the API contract, SQLite persistence, archive degradation,
optional-LLM fallback, CAP safety, report downloads, frontend task flow,
bilingual copy and frozen real-data numerical regression.
