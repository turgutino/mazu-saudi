"""AgentRun: records one orchestration call (见 初步设计.md 第6节 预测智能体).

Not wired into any endpoint yet in v1 (no LLM orchestration is implemented).
Kept as a plain dataclass so a future prediction agent can log its tool calls
without depending on any web framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentRun:
    agent_run_id: str
    request: str
    tool_calls: list[str] = field(default_factory=list)
    prediction_ids: list[str] = field(default_factory=list)
    status: str = "pending"
    started_at: datetime | None = None
    finished_at: datetime | None = None
