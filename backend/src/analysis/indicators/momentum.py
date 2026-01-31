"""
BTC 自动交易系统 — 动量指标

RSI、趋势耗竭检测。
"""

import statistics
from dataclasses import dataclass
from typing import Sequence

from src.common.models import MarketBar


@dataclass
class RSIResult:
    """RSI 结果"""
    value: float
    is_overbought: bool
    is_oversold: bool


@dataclass
class TrendExhaustionResult:
    """趋势耗竭结果"""
    is_exhausted: bool
    direction: str  # up / down
    strength: float
    divergence: bool


def calculate_rsi(
    bars: Sequence[MarketBar],
    period: int = 14,
    overbought: float = 70.0,
    oversold: float = 30.0,
) -> RSIResult:
    """
    计算 RSI（Relative Strength Index）
    
    Args:
        bars: K 线数据
        period: 计算周期
        overbought: 超买阈值
        oversold: 超卖阈值
    
    Returns:
        RSI 结果
    """
    if len(bars) < period + 1:
        return RSIResult(value=50.0, is_overbought=False, is_oversold=False)
    
    # 计算价格变化
    gains = []
    losses = []
    
    for i in range(1, len(bars)):
        change = bars[i].close - bars[i - 1].close
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))
    
    # 取最近 period 个
    recent_gains = gains[-period:]
    recent_losses = losses[-period:]
    
    avg_gain = statistics.mean(recent_gains) if recent_gains else 0.0
    avg_loss = statistics.mean(recent_losses) if recent_losses else 0.0
    
    if avg_loss == 0:
        rsi = 100.0 if avg_gain > 0 else 50.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
    
    return RSIResult(
        value=rsi,
        is_overbought=rsi >= overbought,
        is_oversold=rsi <= oversold,
    )


def detect_trend_exhaustion(
    bars: Sequence[MarketBar],
    rsi_period: int = 14,
    lookback: int = 5,
    divergence_threshold: float = 0.02,
) -> TrendExhaustionResult:
    """
    检测趋势耗竭
    
    通过价格与 RSI 背离检测趋势耗竭：
    - 价格创新高但 RSI 未创新高 → 上涨耗竭
    - 价格创新低但 RSI 未创新低 → 下跌耗竭
    
    Args:
        bars: K 线数据
        rsi_period: RSI 周期
        lookback: 回看周期（检测背离）
        divergence_threshold: 背离阈值
    
    Returns:
        趋势耗竭结果
    """
    if len(bars) < rsi_period + lookback + 1:
        return TrendExhaustionResult(
            is_exhausted=False,
            direction="none",
            strength=0.0,
            divergence=False,
        )
    
    # 计算 RSI 序列
    rsi_values = []
    for i in range(rsi_period, len(bars)):
        rsi = calculate_rsi(bars[:i + 1], rsi_period)
        rsi_values.append(rsi.value)
    
    if len(rsi_values) < lookback:
        return TrendExhaustionResult(
            is_exhausted=False,
            direction="none",
            strength=0.0,
            divergence=False,
        )
    
    # 最近价格和 RSI
    recent_bars = bars[-lookback:]
    recent_rsi = rsi_values[-lookback:]
    
    prices = [b.close for b in recent_bars]
    current_price = prices[-1]
    current_rsi = recent_rsi[-1]
    
    max_price = max(prices[:-1])
    min_price = min(prices[:-1])
    max_rsi = max(recent_rsi[:-1])
    min_rsi = min(recent_rsi[:-1])
    
    # 检测上涨耗竭（价格新高但 RSI 未新高）
    price_new_high = current_price > max_price * (1 + divergence_threshold)
    rsi_not_new_high = current_rsi < max_rsi
    
    if price_new_high and rsi_not_new_high:
        strength = (max_rsi - current_rsi) / max_rsi if max_rsi > 0 else 0.0
        return TrendExhaustionResult(
            is_exhausted=True,
            direction="up",
            strength=min(strength, 1.0),
            divergence=True,
        )
    
    # 检测下跌耗竭（价格新低但 RSI 未新低）
    price_new_low = current_price < min_price * (1 - divergence_threshold)
    rsi_not_new_low = current_rsi > min_rsi
    
    if price_new_low and rsi_not_new_low:
        strength = (current_rsi - min_rsi) / (100 - min_rsi) if min_rsi < 100 else 0.0
        return TrendExhaustionResult(
            is_exhausted=True,
            direction="down",
            strength=min(strength, 1.0),
            divergence=True,
        )
    
    return TrendExhaustionResult(
        is_exhausted=False,
        direction="none",
        strength=0.0,
        divergence=False,
    )
