"""Runtime paths and preflight checks for the historical warning application."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class AppSettings:
    repository_root: Path = REPOSITORY_ROOT
    runtime_root: Path = REPOSITORY_ROOT / "runtime" / "competition_app"

    @property
    def research_assets_root(self) -> Path:
        return self.repository_root / "research" / "historical_warning"

    @property
    def data_file(self) -> Path:
        configured = os.environ.get("MAZU_HISTORICAL_DATA_DIR")
        return (
            Path(configured) / "mazu_dataset.nc"
            if configured
            else self.research_assets_root / "data" / "mazu_dataset.nc"
        )

    @property
    def model_root(self) -> Path:
        return self.research_assets_root / "agent" / "saved_models"

    @property
    def graph_file(self) -> Path:
        return self.research_assets_root / "kg" / "kg_data.json"

    @property
    def database_file(self) -> Path:
        return self.runtime_root / "audit.sqlite3"

    @property
    def artifact_root(self) -> Path:
        return self.runtime_root / "artifacts"

    @property
    def frontend_dist(self) -> Path:
        return self.repository_root / "competition_app" / "dist"

    def preflight(self) -> dict:
        models = [
            self.model_root / f"{hazard}_model.joblib"
            for hazard in ("heatwave", "flash_flood", "dust_storm")
        ]
        ensemble_manifest = self.model_root / "ensemble" / "manifest.json"
        model_meta = self.model_root / "model_meta.json"
        checks = {
            "dataset": self.data_file.is_file(),
            "models": all(path.is_file() for path in models),
            "ensemble": ensemble_manifest.is_file(),
            "model_metadata": model_meta.is_file(),
            "evidence_graph": self.graph_file.is_file(),
        }
        missing = [name for name, available in checks.items() if not available]
        return {
            "mode": "historical_exercise" if not missing else "archive",
            "ready_for_inference": not missing,
            "checks": checks,
            "missing": missing,
            "dataset_path": str(self.data_file),
            "llm_available": bool(os.environ.get("DEEPSEEK_API_KEY")),
        }
