"""
证人健康度管理单元测试
"""

import pytest

from src.common.enums import HealthGrade, WitnessStatus, WitnessTier
from src.common.models import MarketBar, Claim
from src.common.utils import utc_now
from src.strategy.base import BaseStrategy
from src.strategy.health import HealthManager, TradeResult


class MockWitness(BaseStrategy):
    """测试用证人"""
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        return None


class TestHealthManager:
    """健康度管理器测试"""
    
    def test_initialize_health(self):
        """测试初始化健康度"""
        manager = HealthManager()
        witness = MockWitness("test", WitnessTier.TIER_1)
        
        health = manager.initialize_health(witness)
        
        assert health.witness_id == "test"
        assert health.tier == WitnessTier.TIER_1
        assert health.status == WitnessStatus.ACTIVE
        assert health.grade == HealthGrade.B
        assert health.win_rate == 0.5
        assert health.sample_count == 0
    
    def test_update_health_with_wins(self):
        """测试更新健康度（胜利）"""
        manager = HealthManager()
        witness = MockWitness("test", WitnessTier.TIER_1)
        manager.initialize_health(witness)
        
        # 添加 60 次交易，55% 胜率
        for i in range(60):
            result = TradeResult(
                strategy_id="test",
                is_win=i < 33,  # 33/60 = 55%
                pnl=100.0 if i < 33 else -100.0,
                timestamp=utc_now(),
            )
            health = manager.update_health("test", result)
        
        assert health is not None
        assert health.sample_count == 60
        assert health.win_rate == pytest.approx(0.55, rel=0.01)
        assert health.grade == HealthGrade.A
    
    def test_update_health_with_losses(self):
        """测试更新健康度（亏损）"""
        manager = HealthManager()
        witness = MockWitness("test", WitnessTier.TIER_1)
        manager.initialize_health(witness)
        
        # 添加 60 次交易，25% 胜率
        for i in range(60):
            result = TradeResult(
                strategy_id="test",
                is_win=i < 15,  # 15/60 = 25%
                pnl=100.0 if i < 15 else -100.0,
                timestamp=utc_now(),
            )
            health = manager.update_health("test", result)
        
        assert health is not None
        assert health.grade == HealthGrade.D
        assert health.status == WitnessStatus.MUTED
    
    def test_check_auto_mute(self):
        """测试自动静默检查"""
        manager = HealthManager()
        witness = MockWitness("test", WitnessTier.TIER_1)
        manager.initialize_health(witness)
        
        # 添加 60 次交易，20% 胜率
        for i in range(60):
            result = TradeResult(
                strategy_id="test",
                is_win=i < 12,
                pnl=100.0 if i < 12 else -100.0,
                timestamp=utc_now(),
            )
            manager.update_health("test", result)
        
        should_mute = manager.check_auto_mute("test")
        
        assert should_mute is True
    
    def test_insufficient_samples(self):
        """测试样本不足时保持 B 等级"""
        manager = HealthManager()
        witness = MockWitness("test", WitnessTier.TIER_1)
        manager.initialize_health(witness)
        
        # 只添加 10 次交易
        for i in range(10):
            result = TradeResult(
                strategy_id="test",
                is_win=i < 2,  # 20% 胜率
                pnl=100.0 if i < 2 else -100.0,
                timestamp=utc_now(),
            )
            health = manager.update_health("test", result)
        
        assert health is not None
        assert health.grade == HealthGrade.B  # 样本不足，保持 B
        assert health.status == WitnessStatus.ACTIVE
    
    def test_get_health(self):
        """测试获取健康度"""
        manager = HealthManager()
        witness = MockWitness("test", WitnessTier.TIER_1)
        manager.initialize_health(witness)
        
        health = manager.get_health("test")
        
        assert health is not None
        assert health.witness_id == "test"
    
    def test_get_health_nonexistent(self):
        """测试获取不存在的健康度"""
        manager = HealthManager()
        
        health = manager.get_health("nonexistent")
        
        assert health is None
