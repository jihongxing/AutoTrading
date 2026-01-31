"""
证人注册表单元测试
"""

import pytest

from src.common.enums import WitnessTier
from src.strategy.base import BaseStrategy
from src.strategy.registry import WitnessRegistry
from src.common.models import Claim, MarketBar


class MockWitness(BaseStrategy):
    """测试用证人"""
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        return None


class TestWitnessRegistry:
    """证人注册表测试"""
    
    def test_register_witness(self):
        """测试注册证人"""
        registry = WitnessRegistry()
        witness = MockWitness("test", WitnessTier.TIER_1)
        
        registry.register(witness)
        
        assert registry.count == 1
        assert registry.get_witness("test") == witness
    
    def test_unregister_witness(self):
        """测试注销证人"""
        registry = WitnessRegistry()
        witness = MockWitness("test", WitnessTier.TIER_1)
        
        registry.register(witness)
        result = registry.unregister("test")
        
        assert result is True
        assert registry.count == 0
        assert registry.get_witness("test") is None
    
    def test_unregister_nonexistent(self):
        """测试注销不存在的证人"""
        registry = WitnessRegistry()
        
        result = registry.unregister("nonexistent")
        
        assert result is False
    
    def test_get_all_witnesses(self):
        """测试获取所有证人"""
        registry = WitnessRegistry()
        w1 = MockWitness("w1", WitnessTier.TIER_1)
        w2 = MockWitness("w2", WitnessTier.TIER_2)
        
        registry.register(w1)
        registry.register(w2)
        
        witnesses = registry.get_all_witnesses()
        
        assert len(witnesses) == 2
        assert w1 in witnesses
        assert w2 in witnesses
    
    def test_get_by_tier(self):
        """测试按等级获取证人"""
        registry = WitnessRegistry()
        w1 = MockWitness("w1", WitnessTier.TIER_1)
        w2 = MockWitness("w2", WitnessTier.TIER_2)
        w3 = MockWitness("w3", WitnessTier.TIER_1)
        
        registry.register(w1)
        registry.register(w2)
        registry.register(w3)
        
        tier1 = registry.get_by_tier(WitnessTier.TIER_1)
        tier2 = registry.get_by_tier(WitnessTier.TIER_2)
        
        assert len(tier1) == 2
        assert len(tier2) == 1
    
    def test_get_core_witnesses(self):
        """测试获取核心证人"""
        registry = WitnessRegistry()
        w1 = MockWitness("w1", WitnessTier.TIER_1)
        w2 = MockWitness("w2", WitnessTier.TIER_2)
        
        registry.register(w1)
        registry.register(w2)
        
        core = registry.get_core_witnesses()
        
        assert len(core) == 1
        assert w1 in core
    
    def test_get_veto_witnesses(self):
        """测试获取否决证人"""
        registry = WitnessRegistry()
        w1 = MockWitness("w1", WitnessTier.TIER_1)
        w2 = MockWitness("w2", WitnessTier.TIER_3)
        
        registry.register(w1)
        registry.register(w2)
        
        veto = registry.get_veto_witnesses()
        
        assert len(veto) == 1
        assert w2 in veto
    
    def test_get_active_witnesses(self):
        """测试获取激活证人"""
        registry = WitnessRegistry()
        w1 = MockWitness("w1", WitnessTier.TIER_1)
        w2 = MockWitness("w2", WitnessTier.TIER_2)
        
        registry.register(w1)
        registry.register(w2)
        
        w1.mute()
        
        active = registry.get_active_witnesses()
        
        assert len(active) == 1
        assert w2 in active
        assert registry.active_count == 1
