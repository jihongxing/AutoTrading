"""
学习引擎单元测试
"""

import pytest
from datetime import datetime, timedelta
from src.common.utils import utc_now

from src.learning.collector import LearningDataCollector, SignalData, TradeData
from src.learning.engine import LearningEngine
from src.learning.constants import FORBIDDEN_PARAMS


def create_trades(count: int, win_rate: float = 0.55) -> list[TradeData]:
    """创建测试交易数据"""
    trades = []
    for i in range(count):
        is_win = i < int(count * win_rate)
        trades.append(TradeData(
            trade_id=f"t{i}",
            timestamp=utc_now() - timedelta(hours=count - i),
            symbol="BTCUSDT",
            direction="long",
            entry_price=50000.0,
            exit_price=50100.0 if is_win else 49900.0,
            quantity=0.01,
            pnl=100.0 if is_win else -100.0,
            is_win=is_win,
            witness_ids=["w1", "w2"],
            state_at_entry="NORMAL",
            duration_seconds=3600,
        ))
    return trades


def create_signals(count: int, win_rate: float = 0.55) -> list[SignalData]:
    """创建测试信号数据"""
    signals = []
    for i in range(count):
        is_win = i < int(count * win_rate)
        signals.append(SignalData(
            signal_id=f"s{i}",
            timestamp=utc_now() - timedelta(hours=count - i),
            witness_id="w1" if i % 2 == 0 else "w2",
            claim_type="MARKET_ELIGIBLE",
            confidence=0.7,
            direction="long",
            was_executed=True,
            result="win" if is_win else "loss",
        ))
    return signals


class TestLearningEngine:
    """学习引擎测试"""
    
    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        collector = LearningDataCollector()
        engine = LearningEngine(collector)
        return collector, engine
    
    @pytest.mark.asyncio
    async def test_run_daily_learning_insufficient_samples(self, setup):
        """测试每日学习样本不足"""
        collector, engine = setup
        
        # 只添加少量交易
        for trade in create_trades(5):
            collector.record_trade(trade)
        
        report = await engine.run_daily_learning()
        
        assert report.total_trades == 0
        assert report.metadata.get("reason") == "insufficient_samples"
    
    @pytest.mark.asyncio
    async def test_run_daily_learning_success(self, setup):
        """测试每日学习成功"""
        collector, engine = setup
        
        # 添加足够的交易
        for trade in create_trades(20, win_rate=0.6):
            collector.record_trade(trade)
        for signal in create_signals(20, win_rate=0.6):
            collector.record_signal(signal)
        
        report = await engine.run_daily_learning()
        
        assert report.total_trades == 20
        assert report.win_rate == 0.6
        assert report.period == "daily"
    
    @pytest.mark.asyncio
    async def test_run_weekly_learning_success(self, setup):
        """测试每周学习成功"""
        collector, engine = setup
        
        # 添加足够的交易
        for trade in create_trades(60, win_rate=0.55):
            collector.record_trade(trade)
        for signal in create_signals(60, win_rate=0.55):
            collector.record_signal(signal)
        
        report = await engine.run_weekly_learning()
        
        assert report.total_trades == 60
        assert report.period == "weekly"
        assert len(report.weight_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_apply_suggestions_forbidden_param(self, setup):
        """测试应用禁止参数"""
        _, engine = setup
        
        from src.learning.engine import Suggestion
        
        suggestion = Suggestion(
            param_name="max_drawdown",  # 禁止参数
            current_value=0.2,
            suggested_value=0.25,
            action="increase",
            reason="test",
            confidence=0.8,
            requires_approval=False,
        )
        
        result = await engine.apply_suggestions([suggestion], approved=True)
        
        assert "max_drawdown" in result["skipped"]
        assert "max_drawdown" not in result["applied"]
    
    @pytest.mark.asyncio
    async def test_apply_suggestions_requires_approval(self, setup):
        """测试需要审批的建议"""
        _, engine = setup
        
        from src.learning.engine import Suggestion
        
        suggestion = Suggestion(
            param_name="position_multiplier",
            current_value=1.0,
            suggested_value=1.5,
            action="increase",
            reason="test",
            confidence=0.8,
            requires_approval=True,
        )
        
        # 未审批
        result = await engine.apply_suggestions([suggestion], approved=False)
        assert "position_multiplier" in result["skipped"]
        
        # 已审批
        result = await engine.apply_suggestions([suggestion], approved=True)
        assert "position_multiplier" in result["applied"]
    
    def test_witness_weight_management(self, setup):
        """测试证人权重管理"""
        _, engine = setup
        
        engine.set_witness_weight("w1", 0.7)
        
        assert engine.get_witness_weight("w1") == 0.7
        assert engine.get_witness_weight("w2") == 0.5  # 默认值

