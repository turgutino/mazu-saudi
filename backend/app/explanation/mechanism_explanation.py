"""Physical mechanism explanation (初步设计.md 第4节: 物理机制解释).

Answers "why might this happen meteorologically" using static, hand-authored
mechanism templates per hazard — explicitly a *supporting* narrative, not a
claim about the model's real internal computation (RuleBasedForecastModel is
a linear scoring formula, not a causal simulator). Each step is anchored to
an indicator produced by IndicatorProvider so the displayed value is always
the real per-case number, never invented text.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.data.indicator_provider import INDICATOR_SPECS
from app.schemas.common import ConfidenceLevel
from app.schemas.prediction import MechanismPath, MechanismStep


@dataclass(frozen=True)
class _StepTemplate:
    description: str
    indicator: str | None  # key into indicators dict / INDICATOR_SPECS, or None for a static step
    static_value: str | None = None


@dataclass(frozen=True)
class _PathTemplate:
    path_id: str
    path_name: str
    confidence: ConfidenceLevel
    steps: tuple[_StepTemplate, ...]


_TEMPLATES: dict[str, tuple[_PathTemplate, ...]] = {
    "heavy-rain": (
        _PathTemplate(
            "mech-vapor", "水汽输送-对流触发路径", "high",
            (
                _StepTemplate("低层暖湿气流持续输送水汽", "vapor_850"),
                _StepTemplate("大气可降水量显著升高", "pw"),
                _StepTemplate("CAPE累积达到强对流阈值", "cape"),
                _StepTemplate("对流触发，强降水概率上升", "daily_precip"),
            ),
        ),
        _PathTemplate(
            "mech-shear", "风切变组织路径", "medium",
            (
                _StepTemplate("中层风切变增强对流组织性", "shear_500"),
                _StepTemplate("700hPa相对湿度维持高位，抑制蒸发削弱", "rh_700"),
            ),
        ),
    ),
    "extreme-heat": (
        _PathTemplate(
            "mech-subtropical-high", "副高控制高温路径", "high",
            (
                _StepTemplate("850hPa温度异常偏高", "t850"),
                _StepTemplate("500hPa位势高度偏高，下沉气流增强", "h500"),
                _StepTemplate("地表相对湿度降低，晴空辐射增温加剧", "rh_surface"),
                _StepTemplate("近地面温度持续攀升", "t2m"),
            ),
        ),
    ),
    "flash-flood": (
        _PathTemplate(
            "mech-vapor", "水汽输送-地形抬升路径", "high",
            (
                _StepTemplate("低层水汽通量增加", "vapor_850"),
                _StepTemplate("大气可降水量上升", "pw"),
                _StepTemplate("CAPE累积达到强对流阈值", "cape"),
                _StepTemplate("短时强降水引发山洪风险", "daily_precip"),
            ),
        ),
        _PathTemplate(
            "mech-terrain", "地形汇流增强路径", "medium",
            (
                _StepTemplate("700hPa相对湿度维持高位", "rh_700"),
                _StepTemplate("山区地形加速地表径流汇集", None, "地形汇流系数偏高"),
            ),
        ),
    ),
    "dust-storm": (
        _PathTemplate(
            "mech-dry-wind", "干燥强风扬沙路径", "medium",
            (
                _StepTemplate("表层土壤异常干燥", "soil_moisture"),
                _StepTemplate("地表相对湿度偏低，沙尘更易起沙", "rh_surface"),
                _StepTemplate("气压梯度增大产生强风", "wind_10m"),
                _StepTemplate("沙尘扬起，能见度显著下降", "visibility"),
            ),
        ),
    ),
}


def _format_value(indicator_key: str | None, static_value: str | None, indicators: dict[str, float]) -> str:
    if indicator_key is None:
        return static_value or ""
    spec = INDICATOR_SPECS[indicator_key]
    return f"{indicators[indicator_key]:g} {spec.unit}".strip()


def build_mechanisms(hazard: str, indicators: dict[str, float]) -> list[MechanismPath]:
    templates = _TEMPLATES.get(hazard, ())
    paths: list[MechanismPath] = []
    for template in templates:
        steps = [
            MechanismStep(
                step=i + 1,
                description=step.description,
                indicator=INDICATOR_SPECS[step.indicator].label if step.indicator else "地形因子",
                value=_format_value(step.indicator, step.static_value, indicators),
            )
            for i, step in enumerate(template.steps)
        ]
        paths.append(
            MechanismPath(
                path_id=template.path_id,
                path_name=template.path_name,
                confidence=template.confidence,
                steps=steps,
            )
        )
    return paths
