"""
技术指标测试
"""

import pytest
from datetime import datetime, timezone

from src.common.models import MarketBar
from src.analysis import (
    calculate_atr,
    calculate_atr_series,
    detect_compression,
    detect_gap,
    detect_volume_anomaly,
    calculate_rsi,
    detect_trend_exhaustion,
    detect_price_pattern,
    detect_range,
    get_session_info,
    is_trading_favorable,
    PatternType,
)


def create_market_bars(count: int, base_price: float = 50000.0) -> list[MarketBar]:
    """创建测试用 K 线数据"""
    bars = []
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    for i in range(count):
        price = base_price + (i % 10) * 10
        bars.append(MarketBar(
            ts=ts + i * 60000,
            symbol="BTCUSDT",
            interval="1m",
            open=price,
            high=price + 50,
            low=price - 50,
            close=price + 10,
            volume=1000.0,
        ))
    
    return bars


class TestVolatilityIndicators:
    """波动率指标测试"""
    
    def test_calculate_atr(self):
        """测试 ATR 计算"""
        bars = create_market_bars(20)
        atr = calculate_atr(bars, period=14)
        assert atr > 0
    
    def test_calculate_atr_insufficient_data(self):
        """测试数据不足"""
        bars = create_market_bars(1)
        atr = calculate_atr(bars)
        assert atr == 0.0
    
    def test_calculate_atr_series(self):
        """测试 ATR 序列"""
        bars = create_market_bars(30)
        series = calculate_atr_series(bars, period=14)
        assert len(series) > 0
    
    def test_detect_compression(self):
        """测试压缩检测"""
        bars = create_market_bars(150)
        result = detect_compression(bars)
        assert hasattr(result, "is_compressed")
        assert hasattr(result, "ratio")
    
    def test_detect_gap(self):
        """测试跳空检测"""
        bars = create_market_bars(2)
        bars[1] = MarketBar(
            ts=bars[1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50600,  # 跳空
            high=50700,
            low=50500,
            close=50650,
            volume=1000.0,
        )
        
        result = detect_gap(bars[0], bars[1], threshold=0.005)
        assert result.has_gap
        assert result.direction == "up"
    
    def test_detect_volume_anomaly(self):
        """测试成交量异常检测"""
        bars = create_market_bars(30)
        bars[-1] = MarketBar(
            ts=bars[-1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=5000.0,  # 放量
        )
        
        result = detect_volume_anomaly(bars, surge_threshold=2.0)
        assert result.is_anomaly
        assert result.anomaly_type == "surge"


class TestMomentumIndicators:
    """动量指标测试"""
    
    def test_calculate_rsi(self):
        """测试 RSI 计算"""
        bars = create_market_bars(20)
        result = calculate_rsi(bars, period=14)
        assert 0 <= result.value <= 100
    
    def test_rsi_insufficient_data(self):
        """测试数据不足"""
        bars = create_market_bars(5)
        result = calculate_rsi(bars, period=14)
        assert result.value == 50.0
    
    def test_detect_trend_exhaustion(self):
        """测试趋势耗竭检测"""
        bars = create_market_bars(30)
        result = detect_trend_exhaustion(bars)
        assert hasattr(result, "is_exhausted")
        assert hasattr(result, "direction")


class TestPatternIndicators:
    """形态指标测试"""
    
    def test_detect_price_pattern(self):
        """测试价格形态检测"""
        bars = create_market_bars(50)
        result = detect_price_pattern(bars)
        assert hasattr(result, "pattern")
        assert result.pattern in PatternType
    
    def test_detect_range(self):
        """测试区间检测"""
        bars = create_market_bars(50)
        result = detect_range(bars)
        assert hasattr(result, "is_ranging")
        assert hasattr(result, "high")
        assert hasattr(result, "low")
    
    def test_detect_range_insufficient_data(self):
        """测试数据不足"""
        bars = create_market_bars(10)
        result = detect_range(bars, lookback=48)
        assert not result.is_ranging


class TestSessionIndicators:
    """时段指标测试"""
    
    def test_get_session_info(self):
        """测试获取时段信息"""
        info = get_session_info()
        assert hasattr(info, "session")
        assert hasattr(info, "is_high_volatility")
        assert hasattr(info, "is_low_liquidity")
        assert 0 <= info.hour <= 23
    
    def test_is_trading_favorable(self):
        """测试交易时段判断"""
        result = is_trading_favorable()
        assert isinstance(result, bool)
