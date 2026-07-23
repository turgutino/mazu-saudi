"""Transparent soft priors for mechanism applicability."""

import torch


MECHANISM_NAMES = ("advection", "convection", "orography", "persistence")
MECHANISM_FEATURES = (
    "motion_u",
    "motion_v",
    "transport_strength",
    "instability",
    "moisture",
    "upslope_flow",
    "terrain_slope",
    "recent_persistence",
)
AVAILABILITY_FEATURES = ("recent_precipitation", "atmosphere", "terrain")


def applicability_prior(mechanism: torch.Tensor, temperature: float = 0.7) -> torch.Tensor:
    """Map normalized observable states to a four-mechanism soft prior.

    This is a regularizer, not a label. Inputs are expected to be robustly
    scaled; signed wind and upslope components may lie in ``[-1, 1]``.
    """

    if mechanism.ndim != 2 or mechanism.shape[1] != len(MECHANISM_FEATURES):
        raise ValueError(f"mechanism must have {len(MECHANISM_FEATURES)} features")
    u, v, transport, instability, moisture, upslope, slope, persistence = mechanism.unbind(1)
    motion = torch.sqrt(u.square() + v.square() + 1e-8)
    scores = torch.stack(
        (
            motion + transport,
            instability + moisture,
            torch.relu(upslope) + torch.relu(slope),
            persistence + 0.5 * (1.0 - transport.clamp(0, 1)),
        ),
        dim=1,
    )
    return torch.softmax(scores / temperature, dim=1)


def expert_availability(availability: torch.Tensor) -> torch.Tensor:
    """Convert source availability to differentiable expert gates."""

    if availability.ndim != 2 or availability.shape[1] != len(AVAILABILITY_FEATURES):
        raise ValueError(f"availability must have {len(AVAILABILITY_FEATURES)} features")
    precip, atmosphere, terrain = availability.unbind(1)
    return torch.stack(
        (precip * atmosphere, precip * atmosphere, atmosphere * terrain, precip), dim=1
    )
