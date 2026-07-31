"""Application settings for the v1 backend.

No .env / pydantic-settings dependency added — a plain dataclass is enough
for the handful of values v1 needs (CORS origins for the frontend dev
server).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppSettings:
    cors_origins: list[str] = field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    api_prefix: str = "/api/v1"


settings = AppSettings()
