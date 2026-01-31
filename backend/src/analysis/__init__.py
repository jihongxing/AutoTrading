"""
BTC 自动交易系统 — 公共分析模块

提供技术指标和市场分析工具，供检测器和证人复用。
"""

from .indicators import (
    # 波动率
    calculate_atr,
    calculate_atr_series,
    calculate_volatility_ratio,
    detect_compression,
    detect_gap,
    detect_volume_anomaly,
    CompressionResult,
    GapResult,
    VolumeAnomalyResult,
    # 动量
    calculate_rsi,
    detect_trend_exhaustion,
    RSIResult,
    TrendExhaustionResult,
    # 形态
    detect_price_pattern,
    detect_range,
    PatternResult,
    PatternType,
    RangeResult,
    # 时段
    get_session_info,
    is_trading_favorable,
    SessionInfo,
    SessionType,
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
