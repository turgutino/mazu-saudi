"""Application settings for the v1 backend.

No .env / pydantic-settings dependency added — a plain dataclass is enough
for the handful of values v1 needs (CORS origins for the frontend dev
server).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppSettings:
    cors_origins: list[str] = field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
    )
    api_prefix: str = "/api/v1"
    monitor_scheduler_enabled: bool = field(
        default_factory=lambda: _env_flag("MAZU_MONITOR_SCHEDULER_ENABLED", True)
    )


settings = AppSettings()
