"""
策略基类单元测试
"""

import pytest

from src.common.enums import ClaimType, WitnessStatus, WitnessTier
from src.common.exceptions import ArchitectureViolationError, WitnessMutedError
from src.common.models import Claim, MarketBar
from src.common.utils import to_utc_ms, utc_now
from src.strategy.base import BaseStrategy


class MockWitness(BaseStrategy):
    """测试用证人"""
    
    def __init__(self, strategy_id: str = "mock", tier: WitnessTier = WitnessTier.TIER_1):
        super().__init__(strategy_id=strategy_id, tier=tier)
        self._should_generate = False
        self._claim_type = ClaimType.MARKET_ELIGIBLE
        self._confidence = 0.7
        self._direction = "long"
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        if self._should_generate:
            return self.create_claim(
                claim_type=self._claim_type,
                confidence=self._confidence,
                direction=self._direction,
            )
        return None


class TestBaseStrategy:
    """策略基类测试"""
    
    def test_create_witness(self):
        """测试创建证人"""
        witness = MockWitness("test_witness", WitnessTier.TIER_1)
        
        assert witness.strategy_id == "test_witness"
        assert witness.tier == WitnessTier.TIER_1
        assert witness.is_active
        assert witness.is_core_witness
        assert not witness.has_veto_power
    
    def test_tier3_has_veto_power(self):
        """测试 TIER 3 有否决权"""
        witness = MockWitness("veto_witness", WitnessTier.TIER_3)
        
        assert witness.has_veto_power
        assert not witness.is_core_witness
    
    def test_generate_claim(self):
        """测试生成 Claim"""
        witness = MockWitness()
        witness._should_generate = True
        
        now_ms = to_utc_ms(utc_now())
        bars = [
            MarketBar(
                ts=now_ms,
                interval="1h",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0,
            )
        ]
        
        claim = witness.run(bars)
        
        assert claim is not None
        assert claim.strategy_id == "mock"
        assert claim.claim_type == ClaimType.MARKET_ELIGIBLE
        assert claim.confidence == 0.7
        assert claim.direction == "long"
    
    def test_muted_witness_raises_error(self):
        """测试静默证人抛出异常"""
        witness = MockWitness()
        witness.mute()
        
        assert not witness.is_active
        
        with pytest.raises(WitnessMutedError):
            witness.run([])
    
    def test_place_order_raises_error(self):
        """测试下单抛出架构违规异常"""
        witness = MockWitness()
        
        with pytest.raises(ArchitectureViolationError) as exc_info:
            witness.place_order(symbol="BTCUSDT", side="buy", quantity=1.0)
        
        assert "策略无下单权" in str(exc_info.value)
    
    def test_execute_trade_raises_error(self):
        """测试执行交易抛出架构违规异常"""
        witness = MockWitness()
        
        with pytest.raises(ArchitectureViolationError):
            witness.execute_trade()
    
    def test_get_account_balance_raises_error(self):
        """测试获取余额抛出架构违规异常"""
        witness = MockWitness()
        
        with pytest.raises(ArchitectureViolationError):
            witness.get_account_balance()
    
    def test_calculate_position_size_raises_error(self):
        """测试计算仓位抛出架构违规异常"""
        witness = MockWitness()
        
        with pytest.raises(ArchitectureViolationError):
            witness.calculate_position_size(100.0)
    
    def test_activate_witness(self):
        """测试激活证人"""
        witness = MockWitness()
        witness.mute()
        
        assert not witness.is_active
        
        witness.activate()
        
        assert witness.is_active
