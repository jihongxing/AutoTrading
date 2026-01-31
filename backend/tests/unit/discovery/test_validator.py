"""
假设验证器测试
"""

import pytest
from datetime import datetime, timezone

from src.common.enums import HypothesisStatus
from src.discovery.pool.models import Hypothesis, ValidationResult
from src.discovery.validator.engine import HypothesisValidator, MIN_SAMPLE_SIZE
from src.learning.collector import TradeData


def create_trade_data(count: int, win_rate: float = 0.55) -> list[TradeData]:
    """创建测试用交易数据"""
    trades = []
    wins = int(count * win_rate)
    
    for i in range(count):
        is_win = i < wins
        trades.append(TradeData(
            trade_id=f"trade_{i}",
            timestamp=datetime.now(timezone.utc),
            symbol="BTCUSDT",
            direction="long",
            entry_price=50000.0,
            exit_price=50100.0 if is_win else 49900.0,
            quantity=0.1,
            pnl=10.0 if is_win else -10.0,
            is_win=is_win,
            witness_ids=["test_witness"],
            state_at_entry="active_trading",
        ))
    
    return trades


class TestHypothesisValidator:
    """假设验证器测试"""
    
    @pytest.fixture
    def validator(self):
        return HypothesisValidator()
    
    @pytest.fixture
    def sample_hypothesis(self):
        return Hypothesis(
            id="hyp_test_001",
            name="测试假设",
            status=HypothesisStatus.NEW,
            source_detector="volatility",
            source_event="event_001",
            event_definition="test",
            event_params={},
            expected_direction="long",
            expected_win_rate=(0.52, 0.55),
        )

    @pytest.mark.asyncio
    async def test_validate_insufficient_samples(self, validator, sample_hypothesis):
        """测试样本不足"""
        trades = create_trade_data(50)  # 不足 100
        
        result = await validator.validate(sample_hypothesis, trades)
        
        assert result.sample_size == 50
        assert result.p_value == 1.0
        assert result.is_robust is False
    
    @pytest.mark.asyncio
    async def test_validate_tier1(self, validator, sample_hypothesis):
        """测试 TIER_1 验证"""
        trades = create_trade_data(150, win_rate=0.55)
        
        result = await validator.validate(sample_hypothesis, trades)
        
        assert result.sample_size == 150
        assert result.win_rate >= 0.52
        assert result.is_robust is True
    
    @pytest.mark.asyncio
    async def test_validate_fail(self, validator, sample_hypothesis):
        """测试验证失败"""
        trades = create_trade_data(150, win_rate=0.45)
        
        result = await validator.validate(sample_hypothesis, trades)
        
        assert result.win_rate < 0.50
    
    def test_determine_tier_tier1(self, validator):
        """测试判定 TIER_1"""
        result = ValidationResult(
            p_value=0.03,
            win_rate=0.54,
            cohens_d=0.35,
            sample_size=150,
            is_robust=True,
            correlation_max=0.3,
        )
        
        tier = validator.determine_tier(result)
        assert tier == HypothesisStatus.TIER_1
    
    def test_determine_tier_tier2(self, validator):
        """测试判定 TIER_2"""
        result = ValidationResult(
            p_value=0.15,
            win_rate=0.52,
            cohens_d=0.25,
            sample_size=150,
            is_robust=True,
            correlation_max=0.3,
        )
        
        tier = validator.determine_tier(result)
        assert tier == HypothesisStatus.TIER_2
    
    def test_determine_tier_tier3(self, validator):
        """测试判定 TIER_3"""
        result = ValidationResult(
            p_value=0.25,
            win_rate=0.51,
            cohens_d=0.15,
            sample_size=150,
            is_robust=True,
            correlation_max=0.3,
        )
        
        tier = validator.determine_tier(result)
        assert tier == HypothesisStatus.TIER_3
    
    def test_determine_tier_fail(self, validator):
        """测试判定 FAIL"""
        result = ValidationResult(
            p_value=0.5,
            win_rate=0.48,
            cohens_d=0.05,
            sample_size=150,
            is_robust=True,
            correlation_max=0.3,
        )
        
        tier = validator.determine_tier(result)
        assert tier == HypothesisStatus.FAIL
    
    def test_determine_tier_not_robust(self, validator):
        """测试不鲁棒判定 FAIL"""
        result = ValidationResult(
            p_value=0.03,
            win_rate=0.54,
            cohens_d=0.35,
            sample_size=150,
            is_robust=False,  # 不鲁棒
            correlation_max=0.3,
        )
        
        tier = validator.determine_tier(result)
        assert tier == HypothesisStatus.FAIL
    
    def test_check_correlation(self, validator, sample_hypothesis):
        """测试相关性检查"""
        existing_signals = {
            "witness_1": [True, False, True, False, True],
            "witness_2": [False, True, False, True, False],
        }
        hypothesis_signals = [True, False, True, False, True]
        
        max_corr = validator.check_correlation(
            sample_hypothesis,
            existing_signals,
            hypothesis_signals,
        )
        
        assert max_corr == 1.0  # 与 witness_1 完全相关
        assert sample_hypothesis.correlation_with_existing["witness_1"] == 1.0
