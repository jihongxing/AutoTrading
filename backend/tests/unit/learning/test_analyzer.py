"""
后验分析器单元测试
"""

import pytest
from datetime import datetime, timedelta
from src.common.utils import utc_now

from src.learning.analyzer import PostTradeAnalyzer
from src.learning.collector import SignalData, TradeData


def create_trade(
    trade_id: str,
    is_win: bool,
    pnl: float,
    witness_ids: list[str],
    duration: int = 3600,
) -> TradeData:
    """创建测试交易数据"""
    return TradeData(
        trade_id=trade_id,
        timestamp=utc_now(),
        symbol="BTCUSDT",
        direction="long",
        entry_price=50000.0,
        exit_price=50000.0 + pnl / 0.01,
        quantity=0.01,
        pnl=pnl,
        is_win=is_win,
        witness_ids=witness_ids,
        state_at_entry="NORMAL",
        duration_seconds=duration,
    )


def create_signal(
    signal_id: str,
    witness_id: str,
    confidence: float,
    was_executed: bool,
    result: str | None,
) -> SignalData:
    """创建测试信号数据"""
    return SignalData(
        signal_id=signal_id,
        timestamp=utc_now(),
        witness_id=witness_id,
        claim_type="MARKET_ELIGIBLE",
        confidence=confidence,
        direction="long",
        was_executed=was_executed,
        result=result,
    )


class TestPostTradeAnalyzer:
    """后验分析器测试"""
    
    def test_analyze_winning_trade(self):
        """测试分析盈利交易"""
        analyzer = PostTradeAnalyzer()
        trade = create_trade("t1", True, 100.0, ["w1", "w2"])
        
        analysis = analyzer.analyze_trade(trade)
        
        assert analysis.is_win
        assert analysis.pnl == 100.0
        assert analysis.pnl_pct > 0
        assert "w1" in analysis.contributing_witnesses
    
    def test_analyze_losing_trade(self):
        """测试分析亏损交易"""
        analyzer = PostTradeAnalyzer()
        trade = create_trade("t1", False, -150.0, ["w1"], duration=299)
        
        analysis = analyzer.analyze_trade(trade)
        
        assert not analysis.is_win
        assert analysis.pnl == -150.0
        assert "快速止损" in " ".join(analysis.analysis_notes)
    
    def test_analyze_witness_performance(self):
        """测试分析证人表现"""
        analyzer = PostTradeAnalyzer()
        
        trades = [
            create_trade(f"t{i}", i < 6, 100.0 if i < 6 else -100.0, ["w1"])
            for i in range(10)
        ]
        signals = [
            create_signal(f"s{i}", "w1", 0.7, True, "win" if i < 6 else "loss")
            for i in range(10)
        ]
        
        performance = analyzer.analyze_witness_performance("w1", trades, signals)
        
        assert performance.witness_id == "w1"
        assert performance.total_signals == 10
        assert performance.win_count == 6
        assert performance.win_rate == 0.6
    
    def test_analyze_window_accuracy(self):
        """测试分析窗口准确率"""
        analyzer = PostTradeAnalyzer()
        
        signals = [
            create_signal(f"s{i}", "w1", 0.7, True, "win" if i < 7 else "loss")
            for i in range(10)
        ]
        
        analysis = analyzer.analyze_window_accuracy(signals)
        
        assert analysis.total_windows == 10
        assert analysis.accurate_windows == 7
        assert analysis.accuracy_rate == 0.7
    
    def test_insufficient_samples(self):
        """测试样本不足"""
        analyzer = PostTradeAnalyzer()
        
        trades = [create_trade("t1", True, 100.0, ["w1"])]
        signals = [create_signal("s1", "w1", 0.7, True, "win")]
        
        performance = analyzer.analyze_witness_performance("w1", trades, signals)
        
        assert not performance.sample_sufficient

