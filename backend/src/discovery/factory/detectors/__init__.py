"""异常检测器模块"""

from .base import BaseDetector
from .exhaustion import TrendExhaustionDetector
from .funding import FundingDetector
from .funding_volatility import FundingVolatilityDetector
from .gap import GapDetector
from .liquidation import LiquidationDetector
from .pattern import PricePatternDetector
from .session import SessionAnomalyDetector
from .volatility import VolatilityDetector
from .volume import VolumeDetector

__all__ = [
    "BaseDetector",
    # 原有检测器
    "VolatilityDetector",
    "VolumeDetector",
    "FundingDetector",
    "LiquidationDetector",
    # P0 新增检测器
    "PricePatternDetector",
    "GapDetector",
    "TrendExhaustionDetector",
    # P1 新增检测器
    "SessionAnomalyDetector",
    "FundingVolatilityDetector",
]
