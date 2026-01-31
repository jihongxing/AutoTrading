"""技术指标模块"""

from .momentum import (
    RSIResult,
    TrendExhaustionResult,
    calculate_rsi,
    detect_trend_exhaustion,
)
from .pattern import (
    PatternResult,
    PatternType,
    RangeResult,
    detect_price_pattern,
    detect_range,
)
from .session import (
    SessionInfo,
    SessionType,
    get_session_info,
    is_trading_favorable,
)
from .volatility import (
    CompressionResult,
    GapResult,
    VolumeAnomalyResult,
    calculate_atr,
    calculate_atr_series,
    calculate_volatility_ratio,
    detect_compression,
    detect_gap,
    detect_volume_anomaly,
)

__all__ = [
    # 波动率
    "calculate_atr",
    "calculate_atr_series",
    "calculate_volatility_ratio",
    "detect_compression",
    "detect_gap",
    "detect_volume_anomaly",
    "CompressionResult",
    "GapResult",
    "VolumeAnomalyResult",
    # 动量
    "calculate_rsi",
    "detect_trend_exhaustion",
    "RSIResult",
    "TrendExhaustionResult",
    # 形态
    "detect_price_pattern",
    "detect_range",
    "PatternResult",
    "PatternType",
    "RangeResult",
    # 时段
    "get_session_info",
    "is_trading_favorable",
    "SessionInfo",
    "SessionType",
]
