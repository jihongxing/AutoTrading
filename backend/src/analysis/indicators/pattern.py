"""
BTC 自动交易系统 — 形态指标

价格形态、区间检测。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from src.common.models import MarketBar


class PatternType(str, Enum):
    """形态类型"""
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HIGHER_HIGH = "higher_high"
    LOWER_LOW = "lower_low"
    NONE = "none"


@dataclass
class PatternResult:
    """形态检测结果"""
    pattern: PatternType
    confidence: float
    key_levels: list[float]


@dataclass
class RangeResult:
    """区间检测结果"""
    is_ranging: bool
    high: float
    low: float
    width: float
    width_pct: float
    duration: int
    touch_high: int
    touch_low: int


def detect_price_pattern(
    bars: Sequence[MarketBar],
    lookback: int = 48,
    tolerance: float = 0.01,
) -> PatternResult:
    """
    检测价格形态
    
    Args:
        bars: K 线数据
        lookback: 回看周期
        tolerance: 容差（相对于价格）
    
    Returns:
        形态检测结果
    """
    if len(bars) < lookback:
        return PatternResult(
            pattern=PatternType.NONE,
            confidence=0.0,
            key_levels=[],
        )
    
    recent = bars[-lookback:]
    highs = [b.high for b in recent]
    lows = [b.low for b in recent]
    
    # 找局部高点和低点
    local_highs = _find_local_extremes(highs, is_high=True)
    local_lows = _find_local_extremes(lows, is_high=False)
    
    # 检测双顶
    if len(local_highs) >= 2:
        h1, h2 = local_highs[-2], local_highs[-1]
        if abs(h1 - h2) / h1 < tolerance:
            return PatternResult(
                pattern=PatternType.DOUBLE_TOP,
                confidence=0.6,
                key_levels=[h1, h2],
            )
    
    # 检测双底
    if len(local_lows) >= 2:
        l1, l2 = local_lows[-2], local_lows[-1]
        if abs(l1 - l2) / l1 < tolerance:
            return PatternResult(
                pattern=PatternType.DOUBLE_BOTTOM,
                confidence=0.6,
                key_levels=[l1, l2],
            )
    
    # 检测更高高点
    if len(local_highs) >= 2 and local_highs[-1] > local_highs[-2] * (1 + tolerance):
        return PatternResult(
            pattern=PatternType.HIGHER_HIGH,
            confidence=0.55,
            key_levels=[local_highs[-2], local_highs[-1]],
        )
    
    # 检测更低低点
    if len(local_lows) >= 2 and local_lows[-1] < local_lows[-2] * (1 - tolerance):
        return PatternResult(
            pattern=PatternType.LOWER_LOW,
            confidence=0.55,
            key_levels=[local_lows[-2], local_lows[-1]],
        )
    
    return PatternResult(
        pattern=PatternType.NONE,
        confidence=0.0,
        key_levels=[],
    )


def detect_range(
    bars: Sequence[MarketBar],
    lookback: int = 48,
    max_width_pct: float = 0.05,
    min_touches: int = 2,
) -> RangeResult:
    """
    检测价格区间
    
    Args:
        bars: K 线数据
        lookback: 回看周期
        max_width_pct: 最大区间宽度（相对于价格）
        min_touches: 最小触及次数
    
    Returns:
        区间检测结果
    """
    if len(bars) < lookback:
        return RangeResult(
            is_ranging=False,
            high=0.0,
            low=0.0,
            width=0.0,
            width_pct=0.0,
            duration=0,
            touch_high=0,
            touch_low=0,
        )
    
    recent = bars[-lookback:]
    highs = [b.high for b in recent]
    lows = [b.low for b in recent]
    
    range_high = max(highs)
    range_low = min(lows)
    mid_price = (range_high + range_low) / 2
    
    if mid_price == 0:
        return RangeResult(
            is_ranging=False,
            high=range_high,
            low=range_low,
            width=range_high - range_low,
            width_pct=0.0,
            duration=lookback,
            touch_high=0,
            touch_low=0,
        )
    
    width = range_high - range_low
    width_pct = width / mid_price
    
    # 计算触及次数
    touch_high = sum(1 for h in highs if h >= range_high * 0.998)
    touch_low = sum(1 for l in lows if l <= range_low * 1.002)
    
    is_ranging = (
        width_pct <= max_width_pct
        and touch_high >= min_touches
        and touch_low >= min_touches
    )
    
    return RangeResult(
        is_ranging=is_ranging,
        high=range_high,
        low=range_low,
        width=width,
        width_pct=width_pct,
        duration=lookback,
        touch_high=touch_high,
        touch_low=touch_low,
    )


def _find_local_extremes(
    values: list[float],
    is_high: bool,
    window: int = 3,
) -> list[float]:
    """
    找局部极值点
    
    Args:
        values: 数值序列
        is_high: True 找高点，False 找低点
        window: 窗口大小
    
    Returns:
        极值点列表
    """
    if len(values) < window * 2 + 1:
        return []
    
    extremes = []
    
    for i in range(window, len(values) - window):
        left = values[i - window:i]
        right = values[i + 1:i + window + 1]
        current = values[i]
        
        if is_high:
            if current >= max(left) and current >= max(right):
                extremes.append(current)
        else:
            if current <= min(left) and current <= min(right):
                extremes.append(current)
    
    return extremes
