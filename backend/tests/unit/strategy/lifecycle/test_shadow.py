"""
影子运行器测试
"""

import pytest
from unittest.mock import MagicMock

from src.common.enums import ClaimType
from src.common.models import Claim
from src.strategy.lifecycle.shadow import ShadowRunner, MIN_SHADOW_DAYS, MIN_WIN_RATE, MIN_TRADES


def make_claim(strategy_id: str = "test_strategy", direction: str = "long") -> Claim:
    """创建测试用 Claim"""
    return Claim(
        strategy_id=strategy_id,
        claim_type=ClaimType.MARKET_ELIGIBLE,
        confidence=0.7,
        validity_window=300,
        direction=direction,
    )


@pytest.fixture
def shadow_runner():
    return ShadowRunner()


@pytest.fixture
def mock_strategy():
    strategy = MagicMock()
    strategy.strategy_id = "test_strategy"
    strategy.run.return_value = make_claim()
    return strategy


@pytest.fixture
def market_data():
    from src.common.models import MarketBar
    return [
        MarketBar(
            ts=1000000,
            symbol="BTCUSDT",
            interval="1m",
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=100.0,
        )
    ]


class TestShadowRunner:
    """ShadowRunner 测试"""
    
    def test_register_strategy(self, shadow_runner, mock_strategy):
        """注册影子策略"""
        shadow_runner.register_strategy(mock_strategy)
        assert shadow_runner.strategy_count == 1
    
    def test_unregister_strategy(self, shadow_runner, mock_strategy):
        """注销影子策略"""
        shadow_runner.register_strategy(mock_strategy)
        shadow_runner.unregister_strategy("test_strategy")
        assert shadow_runner.strategy_count == 0
    
    @pytest.mark.asyncio
    async def test_run_all(self, shadow_runner, mock_strategy, market_data):
        """运行所有影子策略"""
        shadow_runner.register_strategy(mock_strategy)
        records = await shadow_runner.run_all(market_data)
        
        assert len(records) == 1
        assert records[0].strategy_id == "test_strategy"
        assert records[0].market_price == 50050.0
    
    @pytest.mark.asyncio
    async def test_run_all_empty_data(self, shadow_runner, mock_strategy):
        """空数据不运行"""
        shadow_runner.register_strategy(mock_strategy)
        records = await shadow_runner.run_all([])
        assert len(records) == 0
    
    def test_get_performance_no_records(self, shadow_runner):
        """无记录时绩效为空"""
        perf = shadow_runner.get_performance("nonexistent")
        assert perf is None
    
    def test_get_performance_with_records(self, shadow_runner, mock_strategy):
        """有记录时返回绩效"""
        shadow_runner.register_strategy(mock_strategy)
        
        # 需要有记录才能返回绩效
        claim = make_claim()
        shadow_runner._record_trade("test_strategy", claim, 50000.0)
        
        perf = shadow_runner.get_performance("test_strategy")
        
        assert perf is not None
        assert perf.strategy_id == "test_strategy"
    
    def test_update_trade_result(self, shadow_runner, mock_strategy):
        """更新交易结果"""
        shadow_runner.register_strategy(mock_strategy)
        
        # 记录交易
        claim = make_claim()
        shadow_runner._record_trade("test_strategy", claim, 50000.0)
        
        # 更新结果
        shadow_runner.update_trade_result("test_strategy", 51000.0)
        
        records = shadow_runner.get_records("test_strategy")
        assert len(records) == 1
        assert records[0].simulated_exit == 51000.0
        assert records[0].simulated_pnl == pytest.approx(0.02, rel=0.01)


class TestPromotionConditions:
    """晋升条件测试"""
    
    def test_not_ready_insufficient_days(self, shadow_runner, mock_strategy):
        """天数不足不可晋升"""
        shadow_runner.register_strategy(mock_strategy)
        assert shadow_runner.is_ready_for_promotion("test_strategy") is False
    
    def test_promotion_constants(self):
        """晋升常量"""
        assert MIN_SHADOW_DAYS == 7
        assert MIN_WIN_RATE == 0.51
        assert MIN_TRADES == 10


class TestGetAllPerformances:
    """批量绩效查询测试"""
    
    def test_get_all_performances(self, shadow_runner):
        """获取所有绩效"""
        strategy1 = MagicMock()
        strategy1.strategy_id = "s1"
        strategy2 = MagicMock()
        strategy2.strategy_id = "s2"
        
        shadow_runner.register_strategy(strategy1)
        shadow_runner.register_strategy(strategy2)
        
        # 需要有记录才能返回绩效
        claim = make_claim("s1")
        shadow_runner._record_trade("s1", claim, 50000.0)
        claim2 = make_claim("s2")
        shadow_runner._record_trade("s2", claim2, 50000.0)
        
        perfs = shadow_runner.get_all_performances()
        assert len(perfs) == 2
