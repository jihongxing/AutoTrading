"""假设工厂模块"""

from .detectors import (
    BaseDetector,
    FundingDetector,
    LiquidationDetector,
    VolatilityDetector,
    VolumeDetector,
)
from .engine import HypothesisFactory

__all__ = [
    "HypothesisFactory",
    "BaseDetector",
    "VolatilityDetector",
    "VolumeDetector",
    "FundingDetector",
    "LiquidationDetector",
]
