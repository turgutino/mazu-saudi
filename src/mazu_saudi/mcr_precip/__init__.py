"""Mechanism-constrained routing for precipitation (MCR-Precip)."""

from .contracts import MCRPrecipBatch, MCRPrecipOutput
from .model import MCRPrecip, MCRPrecipConfig

__all__ = ["MCRPrecip", "MCRPrecipBatch", "MCRPrecipConfig", "MCRPrecipOutput"]
