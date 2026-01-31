"""
策略编排器单元测试
"""

import pytest

from src.common.enums import ClaimType, WitnessTier
from src.common.models import Claim, MarketBar
from src.common.utils import to_utc_ms, utc_now
from src.strategy.base import BaseStrategy
from src.strategy.health import HealthManager
from src.strategy.orchestrator import (
    ConflictResolution,
    StrategyOrchestrator,
)
from src.strategy.registry import WitnessRegistry


class MockWitness(BaseStrategy):
    """测试用证人"""
    
    def __init__(
        self,
        strategy_id: str,
        tier: WitnessTier,
        claim_type: ClaimType | None = None,
        confidence: float = 0.7,
        direction: str | None = None,
    ):
        super().__init__(strategy_id=strategy_id, tier=tier)
        self._claim_type = claim_type
        self._confidence = confidence
        self._direction = direction
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        if self._claim_type is None:
            return None
        return self.create_claim(
            claim_type=self._claim_type,
            confidence=self._confidence,
            direction=self._direction,
        )


class TestStrategyOrchestrator:
    """策略编排器测试"""
    
    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        registry = WitnessRegistry()
        health_manager = HealthManager()
        orchestrator = StrategyOrchestrator(registry, health_manager)
        return registry, health_manager, orchestrator
    
    @pytest.fixture
    def market_data(self):
        """测试用市场数据"""
        now_ms = to_utc_ms(utc_now())
        return [
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
    
    @pytest.mark.asyncio
    async def test_run_witnesses(self, setup, market_data):
        """测试运行证人"""
        registry, _, orchestrator = setup
        
        w1 = MockWitness("w1", WitnessTier.TIER_1, ClaimType.MARKET_ELIGIBLE, 0.7, "long")
        w2 = MockWitness("w2", WitnessTier.TIER_2, ClaimType.REGIME_MATCHED, 0.6, "long")
        
        registry.register(w1)
        registry.register(w2)
        
        claims = await orchestrator.run_witnesses(market_data)
        
        assert len(claims) == 2
    
    @pytest.mark.asyncio
    async def test_aggregate_no_claims(self, setup):
        """测试聚合空 Claims"""
        _, _, orchestrator = setup
        
        result = await orchestrator.aggregate_claims([])
        
        assert result.resolution == ConflictResolution.NO_CONFLICT
        assert not result.is_tradeable
    
    @pytest.mark.asyncio
    async def test_aggregate_with_veto(self, setup):
        """测试 TIER 3 否决"""
        registry, _, orchestrator = setup
        
        w1 = MockWitness("w1", WitnessTier.TIER_1, ClaimType.MARKET_ELIGIBLE, 0.7, "long")
        w2 = MockWitness("w2", WitnessTier.TIER_3, ClaimType.EXECUTION_VETO, 1.0)
        
        registry.register(w1)
        registry.register(w2)
        
        claims = [
            w1.create_claim(ClaimType.MARKET_ELIGIBLE, 0.7, "long"),
            w2.create_claim(ClaimType.EXECUTION_VETO, 1.0),
        ]
        
        result = await orchestrator.aggregate_claims(claims)
        
        assert result.resolution == ConflictResolution.VETOED
        assert not result.is_tradeable
        assert result.veto_claim is not None
    
    @pytest.mark.asyncio
    async def test_aggregate_tier1_conflict(self, setup):
        """测试 TIER 1 方向冲突"""
        registry, _, orchestrator = setup
        
        w1 = MockWitness("w1", WitnessTier.TIER_1, ClaimType.MARKET_ELIGIBLE, 0.7, "long")
        w2 = MockWitness("w2", WitnessTier.TIER_1, ClaimType.MARKET_ELIGIBLE, 0.7, "short")
        
        registry.register(w1)
        registry.register(w2)
        
        claims = [
            w1.create_claim(ClaimType.MARKET_ELIGIBLE, 0.7, "long"),
            w2.create_claim(ClaimType.MARKET_ELIGIBLE, 0.7, "short"),
        ]
        
        result = await orchestrator.aggregate_claims(claims)
        
        assert result.resolution == ConflictResolution.REGIME_UNCLEAR
        assert not result.is_tradeable
    
    @pytest.mark.asyncio
    async def test_aggregate_dominant_selected(self, setup):
        """测试选择 DOMINANT"""
        registry, _, orchestrator = setup
        
        w1 = MockWitness("w1", WitnessTier.TIER_1, ClaimType.MARKET_ELIGIBLE, 0.8, "long")
        w2 = MockWitness("w2", WitnessTier.TIER_2, ClaimType.REGIME_MATCHED, 0.6, "long")
        
        registry.register(w1)
        registry.register(w2)
        
        claims = [
            w1.create_claim(ClaimType.MARKET_ELIGIBLE, 0.8, "long"),
            w2.create_claim(ClaimType.REGIME_MATCHED, 0.6, "long"),
        ]
        
        result = await orchestrator.aggregate_claims(claims)
        
        assert result.resolution == ConflictResolution.DOMINANT_SELECTED
        assert result.is_tradeable
        assert result.dominant_claim is not None
        assert result.direction == "long"
    
    @pytest.mark.asyncio
    async def test_high_trading_window_active(self, setup):
        """测试高交易窗口激活"""
        registry, _, orchestrator = setup
        
        w1 = MockWitness("w1", WitnessTier.TIER_1, ClaimType.MARKET_ELIGIBLE, 0.8, "long")
        w2 = MockWitness("w2", WitnessTier.TIER_2, ClaimType.REGIME_MATCHED, 0.6, "long")
        
        registry.register(w1)
        registry.register(w2)
        
        claims = [
            w1.create_claim(ClaimType.MARKET_ELIGIBLE, 0.8, "long"),
            w2.create_claim(ClaimType.REGIME_MATCHED, 0.6, "long"),
        ]
        
        window = await orchestrator.check_high_trading_window(claims)
        
        assert window.is_active
        assert window.direction == "long"
        assert len(window.supporting_witnesses) == 2
    
    @pytest.mark.asyncio
    async def test_high_trading_window_direction_conflict(self, setup):
        """测试高交易窗口方向冲突"""
        registry, _, orchestrator = setup
        
        w1 = MockWitness("w1", WitnessTier.TIER_1, ClaimType.MARKET_ELIGIBLE, 0.8, "long")
        w2 = MockWitness("w2", WitnessTier.TIER_2, ClaimType.REGIME_MATCHED, 0.6, "short")
        
        registry.register(w1)
        registry.register(w2)
        
        claims = [
            w1.create_claim(ClaimType.MARKET_ELIGIBLE, 0.8, "long"),
            w2.create_claim(ClaimType.REGIME_MATCHED, 0.6, "short"),
        ]
        
        window = await orchestrator.check_high_trading_window(claims)
        
        assert not window.is_active
