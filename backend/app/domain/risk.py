"""RiskAssessment: the output of RiskPolicy, strictly separate from RawPrediction.

见 初步设计.md 第3节: Prediction 只是模型算出的概率；RiskAssessment 是结合阈值、
区域敏感度和业务规则之后的风险判断，两者不能互相绕过。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RuleHitRecord:
    rule_id: str
    rule_name: str
    condition: str
    actual_value: str
    threshold: str
    met: bool
    weight: float


@dataclass(frozen=True)
class RiskAssessment:
    risk_level: str  # green | yellow | orange | red
    risk_label: str
    risk_description: str
    rule_hits: list[RuleHitRecord] = field(default_factory=list)
