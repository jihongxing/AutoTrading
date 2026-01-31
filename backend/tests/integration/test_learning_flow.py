"""
自学习层集成测试

测试完整的学习流程：数据收集 → 分析 → 优化建议 → 应用
"""

import pytest
from datetime import datetime, timedelta
from src.common.utils import utc_now

from src.learning import (
    LearningDataCollector,
    LearningEngine,
    LearningParamStorage,
    LearningParams,
    PostTradeAnalyzer,
    StatisticsAnalyzer,
)
from src.learning.collector import SignalData, TradeData


def create_test_trades(count: int, win_rate: float = 0.55) -> list[TradeData]:
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
            witness_ids=["volatility_release", "range_break"],
            state_at_entry="NORMAL",
            duration_seconds=3600 if is_win else 600,
        ))
    return trades


def create_test_signals(count: int, win_rate: float = 0.55) -> list[SignalData]:
    """创建测试信号数据"""
    signals = []
    for i in range(count):
        is_win = i < int(count * win_rate)
        signals.append(SignalData(
            signal_id=f"s{i}",
            timestamp=utc_now() - timedelta(hours=count - i),
            witness_id="volatility_release" if i % 2 == 0 else "range_break",
            claim_type="MARKET_ELIGIBLE",
            confidence=0.7 + (0.1 if is_win else -0.1),
            direction="long",
            was_executed=True,
            result="win" if is_win else "loss",
        ))
    return signals


class TestLearningFlow:
    """学习流程集成测试"""
    
    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        collector = LearningDataCollector()
        analyzer = PostTradeAnalyzer()
        statistics = StatisticsAnalyzer()
        engine = LearningEngine(collector, analyzer, statistics)
        storage = LearningParamStorage(storage_path="data/test_params.json")
        return collector, engine, storage
    
    @pytest.mark.asyncio
    async def test_full_daily_learning_flow(self, setup):
        """测试完整每日学习流程"""
        collector, engine, storage = setup
        
        # 1. 收集数据
        trades = create_test_trades(30, win_rate=0.6)
        signals = create_test_signals(30, win_rate=0.6)
        
        for trade in trades:
            collector.record_trade(trade)
        for signal in signals:
            collector.record_signal(signal)
        
        # 2. 运行学习
        report = await engine.run_daily_learning()
        
        # 3. 验证报告
        assert report.period == "daily"
        # 只有最近 24 小时的数据会被收集
        assert report.total_trades >= 20  # 至少 20 条在 24 小时内
        assert report.win_rate > 0.4
        assert len(report.weight_suggestions) > 0
        
        # 4. 应用建议（模拟审批）
        if report.weight_suggestions:
            from src.learning.engine import Suggestion
            suggestions = [
                Suggestion(
                    param_name=f"weight_{s.witness_id}",
                    current_value=s.current_weight,
                    suggested_value=s.suggested_weight,
                    action=s.action.value,
                    reason=s.reason,
                    confidence=s.confidence,
                    requires_approval=s.requires_approval,
                )
                for s in report.weight_suggestions
            ]
            result = await engine.apply_suggestions(suggestions, approved=True)
            assert len(result["applied"]) > 0 or len(result["skipped"]) > 0
    
    @pytest.mark.asyncio
    async def test_full_weekly_learning_flow(self, setup):
        """测试完整每周学习流程"""
        collector, engine, storage = setup
        
        # 1. 收集数据
        trades = create_test_trades(100, win_rate=0.55)
        signals = create_test_signals(100, win_rate=0.55)
        
        for trade in trades:
            collector.record_trade(trade)
        for signal in signals:
            collector.record_signal(signal)
        
        # 2. 运行学习
        report = await engine.run_weekly_learning()
        
        # 3. 验证报告
        assert report.period == "weekly"
        assert report.total_trades == 100
        assert len(report.weight_suggestions) > 0
        assert len(report.position_suggestions) > 0
        assert len(report.stop_suggestions) > 0
        assert len(report.window_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_param_storage_flow(self, setup):
        """测试参数存储流程"""
        _, _, storage = setup
        
        # 1. 创建新版本
        params = storage.create_new_version()
        params.position_multiplier = 1.2
        params.witness_weights = {"w1": 0.6, "w2": 0.5}
        
        # 2. 保存
        await storage.save_params(params)
        
        # 3. 加载
        loaded = await storage.load_params()
        assert loaded is not None
        assert loaded.position_multiplier == 1.2
        
        # 4. 创建新版本并保存
        params2 = storage.create_new_version(loaded)
        params2.position_multiplier = 1.3
        await storage.save_params(params2)
        
        # 5. 回滚
        rolled_back = await storage.rollback(params.version)
        assert rolled_back is not None
        assert rolled_back.position_multiplier == 1.2
    
    @pytest.mark.asyncio
    async def test_witness_performance_tracking(self, setup):
        """测试证人表现跟踪"""
        collector, engine, _ = setup
        
        # 创建不同表现的证人数据
        trades = []
        signals = []
        
        # w1: 高胜率
        for i in range(40):
            is_win = i < 24  # 60% 胜率
            trades.append(TradeData(
                trade_id=f"t1_{i}",
                timestamp=utc_now() - timedelta(hours=i),
                symbol="BTCUSDT",
                direction="long",
                entry_price=50000.0,
                exit_price=50100.0 if is_win else 49900.0,
                quantity=0.01,
                pnl=100.0 if is_win else -100.0,
                is_win=is_win,
                witness_ids=["w1"],
                state_at_entry="NORMAL",
                duration_seconds=3600,
            ))
            signals.append(SignalData(
                signal_id=f"s1_{i}",
                timestamp=utc_now() - timedelta(hours=i),
                witness_id="w1",
                claim_type="MARKET_ELIGIBLE",
                confidence=0.7,
                direction="long",
                was_executed=True,
                result="win" if is_win else "loss",
            ))
        
        # w2: 低胜率
        for i in range(40):
            is_win = i < 16  # 40% 胜率
            trades.append(TradeData(
                trade_id=f"t2_{i}",
                timestamp=utc_now() - timedelta(hours=i),
                symbol="BTCUSDT",
                direction="long",
                entry_price=50000.0,
                exit_price=50100.0 if is_win else 49900.0,
                quantity=0.01,
                pnl=100.0 if is_win else -100.0,
                is_win=is_win,
                witness_ids=["w2"],
                state_at_entry="NORMAL",
                duration_seconds=3600,
            ))
            signals.append(SignalData(
                signal_id=f"s2_{i}",
                timestamp=utc_now() - timedelta(hours=i),
                witness_id="w2",
                claim_type="MARKET_ELIGIBLE",
                confidence=0.7,
                direction="long",
                was_executed=True,
                result="win" if is_win else "loss",
            ))
        
        for trade in trades:
            collector.record_trade(trade)
        for signal in signals:
            collector.record_signal(signal)
        
        # 运行学习
        report = await engine.run_weekly_learning()
        
        # 验证建议
        w1_suggestion = next(
            (s for s in report.weight_suggestions if s.witness_id == "w1"), None
        )
        w2_suggestion = next(
            (s for s in report.weight_suggestions if s.witness_id == "w2"), None
        )
        
        # w1 应该增加权重，w2 应该减少或静默
        if w1_suggestion:
            assert w1_suggestion.suggested_weight >= w1_suggestion.current_weight
        if w2_suggestion:
            assert w2_suggestion.suggested_weight <= w2_suggestion.current_weight
    
    @pytest.mark.asyncio
    async def test_forbidden_params_protection(self, setup):
        """测试禁止参数保护"""
        _, engine, _ = setup
        
        from src.learning.engine import Suggestion
        
        # 尝试修改禁止参数
        forbidden_suggestions = [
            Suggestion(
                param_name="max_drawdown",
                current_value=0.2,
                suggested_value=0.25,
                action="increase",
                reason="test",
                confidence=0.9,
                requires_approval=False,
            ),
            Suggestion(
                param_name="daily_max_loss",
                current_value=0.03,
                suggested_value=0.05,
                action="increase",
                reason="test",
                confidence=0.9,
                requires_approval=False,
            ),
        ]
        
        result = await engine.apply_suggestions(forbidden_suggestions, approved=True)
        
        # 所有禁止参数都应该被跳过
        assert "max_drawdown" in result["skipped"]
        assert "daily_max_loss" in result["skipped"]
        assert len(result["applied"]) == 0

