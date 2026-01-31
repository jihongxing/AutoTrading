"""
BTC 自动交易系统 — 波动率指标

ATR、波动率压缩、跳空、成交量异常检测。
"""

import statistics
from dataclasses import dataclass
from typing import Sequence

from src.common.models import MarketBar


@dataclass
class CompressionResult:
    """波动率压缩结果"""
    is_compressed: bool
    ratio: float
    current_atr: float
    historical_atr: float


@dataclass
class GapResult:
    """跳空结果"""
    has_gap: bool
    direction: str  # up / down
    gap_size: float
    gap_pct: float


@dataclass
class VolumeAnomalyResult:
    """成交量异常结果"""
    is_anomaly: bool
    ratio: float
    current_volume: float
    avg_volume: float
    anomaly_type: str  # surge / shrink


def calculate_atr(bars: Sequence[MarketBar], period: int = 14) -> float:
    """
    计算 ATR（Average True Range）
    
    Args:
        bars: K 线数据
        period: 计算周期
    
    Returns:
        ATR 值
    """
    if len(bars) < 2:
        return 0.0
    
    true_ranges = []
    for i in range(1, min(len(bars), period + 1)):
        high = bars[i].high
        low = bars[i].low
        prev_close = bars[i - 1].close
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        true_ranges.append(tr)
    
    return statistics.mean(true_ranges) if true_ranges else 0.0


def calculate_atr_series(bars: Sequence[MarketBar], period: int = 14) -> list[float]:
    """
    计算 ATR 序列
    
    Args:
        bars: K 线数据
        period: 计算周期
    
    Returns:
        ATR 序列
    """
    if len(bars) < period + 1:
        return []
    
    # 计算 True Range
    tr_values = []
    for i in range(1, len(bars)):
        high = bars[i].high
        low = bars[i].low
        prev_close = bars[i - 1].close
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        tr_values.append(tr)
    
    # 计算 ATR（简单移动平均）
    atr_values = []
    for i in range(period - 1, len(tr_values)):
        atr = statistics.mean(tr_values[i - period + 1:i + 1])
        atr_values.append(atr)
    
    return atr_values


def calculate_volatility_ratio(
    bars: Sequence[MarketBar],
    current_period: int = 14,
    history_period: int = 100,
) -> float:
    """
    计算波动率比率（当前 ATR / 历史 ATR）
    
    Args:
        bars: K 线数据
        current_period: 当前 ATR 周期
        history_period: 历史 ATR 周期
    
    Returns:
        波动率比率
    """
    if len(bars) < history_period + current_period:
        return 1.0
    
    atr_series = calculate_atr_series(bars, current_period)
    if len(atr_series) < history_period:
        return 1.0
    
    current_atr = atr_series[-1]
    historical_atr = statistics.mean(atr_series[-history_period - 1:-1])
    
    if historical_atr == 0:
        return 1.0
    
    return current_atr / historical_atr


def detect_compression(
    bars: Sequence[MarketBar],
    threshold: float = 0.5,
    atr_period: int = 14,
    history_period: int = 100,
) -> CompressionResult:
    """
    检测波动率压缩
    
    Args:
        bars: K 线数据
        threshold: 压缩阈值（比率低于此值视为压缩）
        atr_period: ATR 周期
        history_period: 历史周期
    
    Returns:
        压缩检测结果
    """
    if len(bars) < history_period + atr_period:
        return CompressionResult(
            is_compressed=False,
            ratio=1.0,
            current_atr=0.0,
            historical_atr=0.0,
        )
    
    atr_series = calculate_atr_series(bars, atr_period)
    if len(atr_series) < history_period:
        return CompressionResult(
            is_compressed=False,
            ratio=1.0,
            current_atr=0.0,
            historical_atr=0.0,
        )
    
    current_atr = atr_series[-1]
    historical_atr = statistics.mean(atr_series[-history_period - 1:-1])
    
    if historical_atr == 0:
        return CompressionResult(
            is_compressed=False,
            ratio=1.0,
            current_atr=current_atr,
            historical_atr=0.0,
        )
    
    ratio = current_atr / historical_atr
    
    return CompressionResult(
        is_compressed=ratio < threshold,
        ratio=ratio,
        current_atr=current_atr,
        historical_atr=historical_atr,
    )


def detect_gap(
    prev_bar: MarketBar,
    current_bar: MarketBar,
    threshold: float = 0.005,
) -> GapResult:
    """
    检测价格跳空
    
    Args:
        prev_bar: 前一根 K 线
        current_bar: 当前 K 线
        threshold: 跳空阈值（相对于价格的比例）
    
    Returns:
        跳空检测结果
    """
    gap = current_bar.open - prev_bar.close
    gap_pct = abs(gap) / prev_bar.close if prev_bar.close > 0 else 0.0
    
    has_gap = gap_pct >= threshold
    direction = "up" if gap > 0 else "down"
    
    return GapResult(
        has_gap=has_gap,
        direction=direction,
        gap_size=abs(gap),
        gap_pct=gap_pct,
    )


def detect_volume_anomaly(
    bars: Sequence[MarketBar],
    surge_threshold: float = 2.0,
    shrink_threshold: float = 0.3,
    lookback: int = 20,
) -> VolumeAnomalyResult:
    """
    检测成交量异常
    
    Args:
        bars: K 线数据
        surge_threshold: 放量阈值（倍数）
        shrink_threshold: 缩量阈值（倍数）
        lookback: 回看周期
    
    Returns:
        成交量异常结果
    """
    if len(bars) < lookback + 1:
        return VolumeAnomalyResult(
            is_anomaly=False,
            ratio=1.0,
            current_volume=0.0,
            avg_volume=0.0,
            anomaly_type="none",
        )
    
    # 历史成交量（不含当前）
    history_volumes = [b.volume for b in bars[-lookback - 1:-1] if b.volume > 0]
    
    if not history_volumes:
        return VolumeAnomalyResult(
            is_anomaly=False,
            ratio=1.0,
            current_volume=bars[-1].volume,
            avg_volume=0.0,
            anomaly_type="none",
        )
    
    avg_volume = statistics.mean(history_volumes)
    current_volume = bars[-1].volume
    
    if avg_volume == 0:
        return VolumeAnomalyResult(
            is_anomaly=False,
            ratio=1.0,
            current_volume=current_volume,
            avg_volume=0.0,
            anomaly_type="none",
        )
    
    ratio = current_volume / avg_volume
    
    if ratio >= surge_threshold:
        return VolumeAnomalyResult(
            is_anomaly=True,
            ratio=ratio,
            current_volume=current_volume,
            avg_volume=avg_volume,
            anomaly_type="surge",
        )
    elif ratio <= shrink_threshold:
        return VolumeAnomalyResult(
            is_anomaly=True,
            ratio=ratio,
            current_volume=current_volume,
            avg_volume=avg_volume,
            anomaly_type="shrink",
        )
    
    return VolumeAnomalyResult(
        is_anomaly=False,
        ratio=ratio,
        current_volume=current_volume,
        avg_volume=avg_volume,
        anomaly_type="none",
    )
