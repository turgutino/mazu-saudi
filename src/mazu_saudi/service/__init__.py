"""Frozen research prototype for the demo-only MCR-Precip product interface."""

from .forecast import DemoForecastService, ForecastRequest

__all__ = ["DemoForecastService", "ForecastRequest"]
