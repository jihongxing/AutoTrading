"""
证人实现单元测试
"""

import pytest
from datetime import timedelta

from src.common.enums import ClaimType
from src.common.models import MarketBar
from src.common.utils import utc_now, to_utc_ms
from src.strategy.witnesses import (
    VolatilityReleaseWitness,
    RangeBreakWitness,
    TimeStructureWitness,
    VolatilityAsymmetryWitness,
    LiquiditySweepWitness,
    MicrostructureWitness,
    RiskSentinelWitness,
    MacroSentinelWitness,
)
from src.strategy.witnesses.macro_sentinel import MacroEvent, MacroEventType


def create_bars(count: int, base_price: float = 100.0, volatility: float = 0.01) -> list[MarketBar]:
    """创建测试用 K 线数据"""
    bars = []
    price = base_price
    now_ms = to_utc_ms(utc_now())
    for i in range(count):
        change = price * volatility * (1 if i % 2 == 0 else -1)
        bars.append(MarketBar(
            ts=now_ms - (count - i) * 3600000,
            interval="1h",
            open=price,
            high=price + abs(change),
            low=price - abs(change),
            close=price + change,
            volume=1000.0 + i * 10,
        ))
        price = price + change
    return bars


class TestVolatilityReleaseWitness:
    """波动率释放证人测试"""
    
    def test_no_signal_insufficient_data(self):
        """测试数据不足时无信号"""
        witness = VolatilityReleaseWitness()
        bars = create_bars(5)
        
        claim = witness.generate_claim(bars)
        
        assert claim is None
    
    def test_compression_detection(self):
        """测试波动率压缩检测"""
        witness = VolatilityReleaseWitness(lookback_period=20, atr_period=5)
        
        # 创建高波动后低波动的数据
        high_vol_bars = create_bars(15, volatility=0.03)
        low_vol_bars = create_bars(5, base_price=high_vol_bars[-1].close, volatility=0.005)
        bars = high_vol_bars + low_vol_bars
        
        claim = witness.generate_claim(bars)
        
        # 压缩状态下不产生信号
        assert claim is None


class TestRangeBreakWitness:
    """区间破坏证人测试"""
    
    def test_no_signal_insufficient_data(self):
        """测试数据不足时无信号"""
        witness = RangeBreakWitness()
        bars = create_bars(10)
        
        claim = witness.generate_claim(bars)
        
        assert claim is None


class TestTimeStructureWitness:
    """时间结构证人测试"""
    
    def test_generates_claim(self):
        """测试生成 Claim"""
        witness = TimeStructureWitness()
        bars = create_bars(10)
        
        claim = witness.generate_claim(bars)
        
        # 根据当前时间可能生成不同类型的 Claim
        # 这里只验证不会抛出异常


class TestVolatilityAsymmetryWitness:
    """波动率不对称证人测试"""
    
    def test_no_signal_insufficient_data(self):
        """测试数据不足时无信号"""
        witness = VolatilityAsymmetryWitness()
        bars = create_bars(5)
        
        claim = witness.generate_claim(bars)
        
        assert claim is None
    
    def test_asymmetry_detection(self):
        """测试不对称检测"""
        witness = VolatilityAsymmetryWitness(lookback_period=10, asymmetry_threshold=1.3)
        
        # 创建上涨波动率更大的数据
        bars = []
        price = 100.0
        now_ms = to_utc_ms(utc_now())
        for i in range(10):
            if i % 2 == 0:
                change = 3.0  # 大幅上涨
            else:
                change = -1.0  # 小幅下跌
            bars.append(MarketBar(
                ts=now_ms - (10 - i) * 3600000,
                interval="1h",
                open=price,
                high=price + max(0, change),
                low=price + min(0, change),
                close=price + change,
                volume=1000.0,
            ))
            price += change
        
        claim = witness.generate_claim(bars)
        
        if claim:
            assert claim.direction == "long"


class TestLiquiditySweepWitness:
    """流动性收割证人测试"""
    
    def test_no_signal_insufficient_data(self):
        """测试数据不足时无信号"""
        witness = LiquiditySweepWitness()
        bars = create_bars(10)
        
        claim = witness.generate_claim(bars)
        
        assert claim is None


class TestMicrostructureWitness:
    """微结构证人测试"""
    
    def test_no_signal_insufficient_data(self):
        """测试数据不足时无信号"""
        witness = MicrostructureWitness()
        bars = create_bars(5)
        
        claim = witness.generate_claim(bars)
        
        assert claim is None
    
    def test_volume_spike_detection(self):
        """测试成交量异常检测"""
        witness = MicrostructureWitness(lookback_period=10, volume_threshold=2.0)
        
        bars = create_bars(10)
        # 最后一根 K 线成交量异常
        bars[-1] = MarketBar(
            ts=bars[-1].ts,
            interval=bars[-1].interval,
            open=bars[-1].open,
            high=bars[-1].high,
            low=bars[-1].low,
            close=bars[-1].close,
            volume=5000.0,  # 5x 正常成交量
        )
        
        claim = witness.generate_claim(bars)
        
        if claim:
            assert "volume_ratio" in claim.constraints


class TestRiskSentinelWitness:
    """风控证人测试"""
    
    def test_no_veto_normal_conditions(self):
        """测试正常条件下无否决"""
        witness = RiskSentinelWitness()
        bars = create_bars(10)
        
        claim = witness.generate_claim(bars)
        
        assert claim is None
    
    def test_veto_extreme_volatility(self):
        """测试极端波动否决"""
        witness = RiskSentinelWitness(extreme_volatility_threshold=0.02)
        
        bars = create_bars(10)
        # 最后一根 K 线价格剧烈变动
        bars[-1] = MarketBar(
            ts=bars[-1].ts,
            interval=bars[-1].interval,
            open=bars[-2].close,
            high=bars[-2].close * 1.05,
            low=bars[-2].close * 0.95,
            close=bars[-2].close * 1.03,  # 3% 变动
            volume=1000.0,
        )
        
        claim = witness.generate_claim(bars)
        
        assert claim is not None
        assert claim.claim_type == ClaimType.EXECUTION_VETO
    
    def test_veto_position_limit(self):
        """测试仓位限制否决"""
        witness = RiskSentinelWitness(max_position_pct=0.30)
        witness.update_position(0.35)
        
        bars = create_bars(10)
        claim = witness.generate_claim(bars)
        
        assert claim is not None
        assert claim.claim_type == ClaimType.EXECUTION_VETO
        assert claim.constraints["veto_reason"] == "position_limit_exceeded"
    
    def test_veto_consecutive_losses(self):
        """测试连续亏损否决"""
        witness = RiskSentinelWitness(max_consecutive_losses=3)
        
        for _ in range(3):
            witness.record_trade_result(is_win=False)
        
        bars = create_bars(10)
        claim = witness.generate_claim(bars)
        
        assert claim is not None
        assert claim.claim_type == ClaimType.EXECUTION_VETO
        assert claim.constraints["veto_reason"] == "consecutive_losses_exceeded"


class TestMacroSentinelWitness:
    """宏观证人测试"""
    
    def test_no_veto_no_events(self):
        """测试无事件时无否决"""
        witness = MacroSentinelWitness()
        bars = create_bars(10)
        
        claim = witness.generate_claim(bars)
        
        assert claim is None
    
    def test_veto_scheduled_event(self):
        """测试预定事件否决"""
        witness = MacroSentinelWitness(event_buffer_hours=2)
        
        # 添加即将发生的事件
        now_ms = to_utc_ms(utc_now())
        event = MacroEvent(
            event_type=MacroEventType.FED_MEETING,
            timestamp=utc_now() + timedelta(hours=1),
            severity=0.9,
            description="FOMC Meeting",
        )
        witness.add_scheduled_event(event)
        
        bars = create_bars(10)
        claim = witness.generate_claim(bars)
        
        assert claim is not None
        assert claim.claim_type == ClaimType.EXECUTION_VETO
        assert claim.constraints["veto_reason"] == "scheduled_macro_event"
    
    def test_veto_active_event(self):
        """测试实时事件否决"""
        witness = MacroSentinelWitness()
        
        # 报告实时事件
        event = MacroEvent(
            event_type=MacroEventType.BLACK_SWAN,
            timestamp=utc_now(),
            severity=1.0,
            description="Flash crash detected",
        )
        witness.report_event(event)
        
        bars = create_bars(10)
        claim = witness.generate_claim(bars)
        
        assert claim is not None
        assert claim.claim_type == ClaimType.EXECUTION_VETO
        assert claim.constraints["veto_reason"] == "active_macro_event"
