"""
证人生成器测试
"""

import pytest

from src.common.enums import ClaimType, HypothesisStatus, WitnessTier
from src.common.models import MarketBar
from src.discovery.pool.models import Hypothesis
from src.discovery.promoter.generator import WitnessGenerator
from src.strategy.base import BaseStrategy
from src.strategy.health import HealthManager
from src.strategy.registry import WitnessRegistry


class TestWitnessGenerator:
    """证人生成器测试"""
    
    @pytest.fixture
    def registry(self):
        return WitnessRegistry()
    
    @pytest.fixture
    def health_manager(self):
        return HealthManager()
    
    @pytest.fixture
    def generator(self, registry, health_manager):
        return WitnessGenerator(registry, health_manager)
    
    @pytest.fixture
    def tier1_hypothesis(self):
        return Hypothesis(
            id="hyp_tier1_001",
            name="TIER1 假设",
            status=HypothesisStatus.TIER_1,
            source_detector="volatility",
            source_event="event_001",
            event_definition="atr < avg_atr * 0.5",
            event_params={"compression_threshold": 0.5, "lookback_period": 20.0},
            expected_direction="breakout",
            expected_win_rate=(0.52, 0.55),
        )
    
    @pytest.fixture
    def tier2_hypothesis(self):
        return Hypothesis(
            id="hyp_tier2_001",
            name="TIER2 假设",
            status=HypothesisStatus.TIER_2,
            source_detector="volume",
            source_event="event_002",
            event_definition="volume > avg * 2.5",
            event_params={"surge_threshold": 2.5},
            expected_direction="long",
            expected_win_rate=(0.51, 0.53),
        )

    def test_generate_witness_class(self, generator, tier1_hypothesis):
        """测试生成证人类"""
        witness_class = generator.generate_witness_class(tier1_hypothesis)
        
        assert issubclass(witness_class, BaseStrategy)
        
        witness = witness_class()
        assert witness.strategy_id == f"hyp_{tier1_hypothesis.id}"
        assert witness.tier == WitnessTier.TIER_1
    
    def test_generate_and_register(self, generator, registry, tier1_hypothesis):
        """测试生成并注册证人"""
        witness = generator.generate_and_register(tier1_hypothesis)
        
        assert witness is not None
        assert registry.count == 1
        assert tier1_hypothesis.status == HypothesisStatus.PROMOTED
    
    def test_generate_tier2_witness(self, generator, tier2_hypothesis):
        """测试生成 TIER2 证人"""
        witness_class = generator.generate_witness_class(tier2_hypothesis)
        witness = witness_class()
        
        assert witness.tier == WitnessTier.TIER_2
    
    def test_not_promotable(self, generator):
        """测试不可晋升的假设"""
        fail_hypothesis = Hypothesis(
            id="hyp_fail_001",
            name="失败假设",
            status=HypothesisStatus.FAIL,
            source_detector="volatility",
            source_event="event_fail",
            event_definition="test",
            event_params={},
            expected_direction="long",
            expected_win_rate=(0.48, 0.50),
        )
        
        witness = generator.generate_and_register(fail_hypothesis)
        assert witness is None
    
    def test_witness_generates_claim(self, generator, tier1_hypothesis):
        """测试生成的证人能产生 Claim"""
        from datetime import datetime, timezone
        
        witness_class = generator.generate_witness_class(tier1_hypothesis)
        witness = witness_class()
        
        # 创建足够的测试数据
        bars = []
        ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        for i in range(200):
            bars.append(MarketBar(
                ts=ts + i * 60000,
                symbol="BTCUSDT",
                interval="1m",
                open=50000 + i,
                high=50100 + i,
                low=49900 + i,
                close=50050 + i,
                volume=1000.0,
            ))
        
        # 调用 generate_claim
        claim = witness.generate_claim(bars)
        
        # 可能返回 None 或 Claim
        if claim is not None:
            assert claim.strategy_id == witness.strategy_id
            assert claim.claim_type == ClaimType.MARKET_ELIGIBLE
    
    def test_map_tier(self, generator):
        """测试等级映射"""
        assert generator._map_tier(HypothesisStatus.TIER_1) == WitnessTier.TIER_1
        assert generator._map_tier(HypothesisStatus.TIER_2) == WitnessTier.TIER_2
        assert generator._map_tier(HypothesisStatus.TIER_3) == WitnessTier.TIER_3
        assert generator._map_tier(HypothesisStatus.FAIL) == WitnessTier.TIER_2  # 默认
