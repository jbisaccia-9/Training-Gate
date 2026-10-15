"""Training Gate: automate document-based compliance training end to end."""

from .config import BrandTheme, GateConfig
from .engine import RunReport, TrainingGate, is_acknowledgement
from .state import JsonStateStore

__all__ = ["BrandTheme", "GateConfig", "JsonStateStore", "RunReport", "TrainingGate", "is_acknowledgement"]
__version__ = "0.1.0"
