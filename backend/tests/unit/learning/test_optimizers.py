"""
优化器单元测试
"""

import pytest
from datetime import datetime
from src.common.utils import utc_now

from src.learning.analyzer import WitnessPerformance, WindowAnalysis
from src.learning.collector import TradeData
from src.learning.optimizers import (
    PositionOptimizer,
    StopOptimizer,
    WeightOptimizer,
    WindowOptimizer,
)
from src.learning.optimizers.weight import WeightAction
from src.learning.optimizers.position import PositionAction
from src.learning.optimizers.stop import StopAction
from src.learning.optimizers.window import WindowAction
from src.learning.statistics import PnLStatistics


def create_performance(
    witness_id: str,
    win_rate: float,
    sample_count: int = 50,
) -> WitnessPerformance:
    """创建测试证人表现"""
    return WitnessPerformance(
        witness_id=witness_id,
        total_signals=sample_count,
        executed_signals=sample_count,
        win_count=int(sample_count * win_rate),
        loss_count=sample_count - int(sample_count * win_rate),
        win_rate=win_rate,
        avg_pnl=100.0 if win_rate > 0.5 else -50.0,
        total_pnl=100.0 * sample_count if win_rate > 0.5 else -50.0 * sample_count,
        avg_confidence=0.7,
        confidence_accuracy=0.6,
        sample_sufficient=sample_count >= 30,
    )


def create_pnl_stats(
    total_trades: int,
    win_rate: float,
    profit_factor: float = 1.5,
) -> PnLStatistics:
    """创建测试盈亏统计"""
    win_count = int(total_trades * win_rate)
    return PnLStatistics(
        total_trades=total_trades,
        win_count=win_count,
        loss_count=total_trades - win_count,
        win_rate=win_rate,
        total_pnl=1000.0,
        avg_pnl=1000.0 / total_trades,
        avg_win=100.0,
        avg_loss=50.0,
        profit_factor=profit_factor,
        expectancy=50.0,
    )


class TestWeightOptimizer:
    """权重优化器测试"""
    
    def test_increase_weight_high_win_rate(self):
        """测试高胜率增加权重"""
        optimizer = WeightOptimizer()
        performance = create_performance("w1", 0.58)
        
        suggestion = optimizer.suggest_weight_adjustment("w1", performance, 0.5)
        
        assert suggestion.action == WeightAction.INCREASE
        assert suggestion.suggested_weight > 0.5
    
    def test_maintain_weight_normal_win_rate(self):
        """测试正常胜率保持权重"""
        optimizer = WeightOptimizer()
        performance = create_performance("w1", 0.53)
        
        suggestion = optimizer.suggest_weight_adjustment("w1", performance, 0.5)
        
        assert suggestion.action == WeightAction.MAINTAIN
        assert suggestion.suggested_weight == 0.5
    
    def test_decrease_weight_low_win_rate(self):
        """测试低胜率减少权重"""
        optimizer = WeightOptimizer()
        performance = create_performance("w1", 0.49)
        
        suggestion = optimizer.suggest_weight_adjustment("w1", performance, 0.5)
        
        assert suggestion.action == WeightAction.DECREASE
        assert suggestion.suggested_weight < 0.5
    
    def test_mute_very_low_win_rate(self):
        """测试极低胜率静默"""
        optimizer = WeightOptimizer()
        performance = create_performance("w1", 0.45)
        
        suggestion = optimizer.suggest_weight_adjustment("w1", performance, 0.5)
        
        assert suggestion.action == WeightAction.MUTE
    
    def test_maintain_insufficient_samples(self):
        """测试样本不足保持"""
        optimizer = WeightOptimizer()
        performance = create_performance("w1", 0.60, sample_count=10)
        
        suggestion = optimizer.suggest_weight_adjustment("w1", performance, 0.5)
        
        assert suggestion.action == WeightAction.MAINTAIN
        assert "样本量不足" in suggestion.reason


class TestPositionOptimizer:
    """仓位优化器测试"""
    
    def test_increase_multiplier_good_performance(self):
        """测试表现好增加放大系数"""
        optimizer = PositionOptimizer()
        stats = create_pnl_stats(60, 0.58)
        
        suggestion = optimizer.suggest_multiplier_adjustment(stats, 1.0, 1.5)
        
        assert suggestion.action == PositionAction.INCREASE
        assert suggestion.suggested_value > 1.0
    
    def test_decrease_multiplier_poor_performance(self):
        """测试表现差减少放大系数"""
        optimizer = PositionOptimizer()
        stats = create_pnl_stats(60, 0.45)
        
        suggestion = optimizer.suggest_multiplier_adjustment(stats, 1.0, 0.3)
        
        assert suggestion.action == PositionAction.DECREASE
        assert suggestion.suggested_value < 1.0
    
    def test_maintain_insufficient_samples(self):
        """测试样本不足保持"""
        optimizer = PositionOptimizer()
        stats = create_pnl_stats(20, 0.60)
        
        suggestion = optimizer.suggest_multiplier_adjustment(stats, 1.0, 1.5)
        
        assert suggestion.action == PositionAction.MAINTAIN


class TestStopOptimizer:
    """止损止盈优化器测试"""
    
    def test_loosen_stop_loss_high_trigger_rate(self):
        """测试止损触发率高时放宽"""
        optimizer = StopOptimizer()
        
        # 创建大量快速止损的交易
        trades = [
            TradeData(
                trade_id=f"t{i}",
                timestamp=utc_now(),
                symbol="BTCUSDT",
                direction="long",
                entry_price=50000.0,
                exit_price=49000.0,
                quantity=0.01,
                pnl=-100.0,
                is_win=False,
                witness_ids=["w1"],
                state_at_entry="NORMAL",
                duration_seconds=300,  # 快速止损
            )
            for i in range(50)
        ] + [
            TradeData(
                trade_id=f"tw{i}",
                timestamp=utc_now(),
                symbol="BTCUSDT",
                direction="long",
                entry_price=50000.0,
                exit_price=51000.0,
                quantity=0.01,
                pnl=100.0,
                is_win=True,
                witness_ids=["w1"],
                state_at_entry="NORMAL",
                duration_seconds=3600,
            )
            for i in range(50)
        ]
        
        suggestion = optimizer.suggest_stop_loss_adjustment(trades, 0.02)
        
        assert suggestion.action == StopAction.LOOSEN
    
    def test_maintain_insufficient_samples(self):
        """测试样本不足保持"""
        optimizer = StopOptimizer()
        trades = []
        
        suggestion = optimizer.suggest_stop_loss_adjustment(trades, 0.02)
        
        assert suggestion.action == StopAction.MAINTAIN


class TestWindowOptimizer:
    """窗口优化器测试"""
    
    def test_raise_threshold_high_fp(self):
        """测试假阳性高时提高阈值"""
        optimizer = WindowOptimizer()
        analysis = WindowAnalysis(
            total_windows=50,
            accurate_windows=30,
            accuracy_rate=0.6,
            avg_confidence=0.7,
            false_positive_rate=0.4,
            false_negative_rate=0.1,
        )
        
        suggestion = optimizer.suggest_threshold_adjustment(analysis, 0.6)
        
        assert suggestion.action == WindowAction.RAISE_THRESHOLD
        assert suggestion.suggested_value > 0.6
    
    def test_lower_threshold_high_fn(self):
        """测试假阴性高时降低阈值"""
        optimizer = WindowOptimizer()
        analysis = WindowAnalysis(
            total_windows=50,
            accurate_windows=40,
            accuracy_rate=0.8,
            avg_confidence=0.7,
            false_positive_rate=0.1,
            false_negative_rate=0.3,
        )
        
        suggestion = optimizer.suggest_threshold_adjustment(analysis, 0.6)
        
        assert suggestion.action == WindowAction.LOWER_THRESHOLD
        assert suggestion.suggested_value < 0.6

