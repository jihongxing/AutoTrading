"""
BTC 自动交易系统 — 假设工厂（策略发现引擎）

自动检测市场异常、生成策略假设、验证并晋升为证人。
"""

from .factory import (
    BaseDetector,
    FundingDetector,
    HypothesisFactory,
    LiquidationDetector,
    VolatilityDetector,
    VolumeDetector,
)
from .pool import AnomalyEvent, Hypothesis, HypothesisPoolManager, ValidationResult
from .promoter import WitnessGenerator
from .validator import HypothesisValidator

__all__ = [
    "HypothesisFactory",
    "BaseDetector",
    "VolatilityDetector",
    "VolumeDetector",
    "FundingDetector",
    "LiquidationDetector",
    "AnomalyEvent",
    "Hypothesis",
    "ValidationResult",
    "HypothesisPoolManager",
    "HypothesisValidator",
    "WitnessGenerator",
]
