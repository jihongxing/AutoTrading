"""
BTC 自动交易系统 — 后验分析器

分析交易结果和证人表现。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.logging import get_logger

from .collector import SignalData, TradeData
from .constants import SampleRequirements

logger = get_logger(__name__)


@dataclass
class TradeAnalysis:
    """交易分析结果"""
    trade_id: str
    is_win: bool
    pnl: float
    pnl_pct: float
    duration_seconds: int
    entry_quality: float  # 入场质量评分
    exit_quality: float  # 出场质量评分
    contributing_witnesses: list[str]
    analysis_notes: list[str] = field(default_factory=list)


@dataclass
class WitnessPerformance:
    """证人表现"""
    witness_id: str
    total_signals: int
    executed_signals: int
    win_count: int
    loss_count: int
    win_rate: float
    avg_pnl: float
    total_pnl: float
    avg_confidence: float
    confidence_accuracy: float  # 置信度与实际结果的相关性
    sample_sufficient: bool


@dataclass
class WindowAnalysis:
    """窗口分析结果"""
    total_windows: int
    accurate_windows: int
    accuracy_rate: float
    avg_confidence: float
    false_positive_rate: float
    false_negative_rate: float


class PostTradeAnalyzer:
    """
    后验分析器
    
    分析交易结果：
    - 成功/失败分析
    - 证人表现分析
    - 窗口准确率分析
    """
    
    def analyze_trade(self, trade: TradeData) -> TradeAnalysis:
        """
        分析单笔交易
        
        Args:
            trade: 交易数据
        
        Returns:
            交易分析结果
        """
        # 计算盈亏百分比
        pnl_pct = trade.pnl / (trade.entry_price * trade.quantity) if trade.quantity > 0 else 0
        
        # 评估入场质量
        entry_quality = self._evaluate_entry_quality(trade)
        
        # 评估出场质量
        exit_quality = self._evaluate_exit_quality(trade)
        
        # 生成分析备注
        notes = []
        if trade.is_win:
            if pnl_pct > 0.02:
                notes.append("优秀交易：盈利超过 2%")
            elif pnl_pct > 0.01:
                notes.append("良好交易：盈利超过 1%")
        else:
            if pnl_pct < -0.02:
                notes.append("需要关注：亏损超过 2%")
            if trade.duration_seconds < 300:
                notes.append("快速止损：持仓时间短")
        
        return TradeAnalysis(
            trade_id=trade.trade_id,
            is_win=trade.is_win,
            pnl=trade.pnl,
            pnl_pct=pnl_pct,
            duration_seconds=trade.duration_seconds,
            entry_quality=entry_quality,
            exit_quality=exit_quality,
            contributing_witnesses=trade.witness_ids,
            analysis_notes=notes,
        )
    
    def analyze_witness_performance(
        self,
        witness_id: str,
        trades: list[TradeData],
        signals: list[SignalData],
    ) -> WitnessPerformance:
        """
        分析证人表现
        
        Args:
            witness_id: 证人 ID
            trades: 相关交易数据
            signals: 相关信号数据
        
        Returns:
            证人表现
        """
        # 过滤该证人的交易
        witness_trades = [t for t in trades if witness_id in t.witness_ids]
        witness_signals = [s for s in signals if s.witness_id == witness_id]
        
        total_signals = len(witness_signals)
        executed_signals = sum(1 for s in witness_signals if s.was_executed)
        
        win_count = sum(1 for t in witness_trades if t.is_win)
        loss_count = len(witness_trades) - win_count
        
        win_rate = win_count / len(witness_trades) if witness_trades else 0.0
        
        total_pnl = sum(t.pnl for t in witness_trades)
        avg_pnl = total_pnl / len(witness_trades) if witness_trades else 0.0
        
        avg_confidence = (
            sum(s.confidence for s in witness_signals) / total_signals
            if total_signals > 0 else 0.0
        )
        
        # 计算置信度准确性
        confidence_accuracy = self._calculate_confidence_accuracy(witness_signals)
        
        # 检查样本量是否足够
        sample_sufficient = len(witness_trades) >= SampleRequirements.MIN_TRADES_FOR_WEIGHT
        
        logger.info(
            f"证人表现分析: {witness_id}, 胜率: {win_rate:.2%}, 样本: {len(witness_trades)}",
            extra={"witness_id": witness_id, "win_rate": win_rate, "sample_count": len(witness_trades)},
        )
        
        return WitnessPerformance(
            witness_id=witness_id,
            total_signals=total_signals,
            executed_signals=executed_signals,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            avg_pnl=avg_pnl,
            total_pnl=total_pnl,
            avg_confidence=avg_confidence,
            confidence_accuracy=confidence_accuracy,
            sample_sufficient=sample_sufficient,
        )
    
    def analyze_window_accuracy(
        self,
        signals: list[SignalData],
    ) -> WindowAnalysis:
        """
        分析窗口判定准确率
        
        Args:
            signals: 信号数据
        
        Returns:
            窗口分析结果
        """
        # 过滤有结果的信号
        completed_signals = [s for s in signals if s.result in ("win", "loss")]
        
        if not completed_signals:
            return WindowAnalysis(
                total_windows=0,
                accurate_windows=0,
                accuracy_rate=0.0,
                avg_confidence=0.0,
                false_positive_rate=0.0,
                false_negative_rate=0.0,
            )
        
        total = len(completed_signals)
        accurate = sum(1 for s in completed_signals if s.result == "win")
        
        # 计算假阳性和假阴性
        executed = [s for s in completed_signals if s.was_executed]
        not_executed = [s for s in signals if not s.was_executed and s.result]
        
        false_positives = sum(1 for s in executed if s.result == "loss")
        false_negatives = sum(1 for s in not_executed if s.result == "win")
        
        fp_rate = false_positives / len(executed) if executed else 0.0
        fn_rate = false_negatives / len(not_executed) if not_executed else 0.0
        
        return WindowAnalysis(
            total_windows=total,
            accurate_windows=accurate,
            accuracy_rate=accurate / total,
            avg_confidence=sum(s.confidence for s in completed_signals) / total,
            false_positive_rate=fp_rate,
            false_negative_rate=fn_rate,
        )
    
    def _evaluate_entry_quality(self, trade: TradeData) -> float:
        """评估入场质量"""
        # 简化评估：基于最终结果和持仓时间
        if trade.is_win:
            return min(1.0, 0.6 + trade.duration_seconds / 3600 * 0.2)
        else:
            return max(0.0, 0.4 - abs(trade.pnl) / (trade.entry_price * trade.quantity) * 2)
    
    def _evaluate_exit_quality(self, trade: TradeData) -> float:
        """评估出场质量"""
        if trade.exit_price is None:
            return 0.5
        
        # 简化评估
        if trade.is_win:
            return 0.7
        else:
            # 快速止损得分更高
            if trade.duration_seconds < 600:
                return 0.6
            return 0.4
    
    def _calculate_confidence_accuracy(self, signals: list[SignalData]) -> float:
        """计算置信度准确性"""
        if not signals:
            return 0.0
        
        # 高置信度信号的成功率
        high_conf_signals = [s for s in signals if s.confidence >= 0.7 and s.result]
        if not high_conf_signals:
            return 0.5
        
        wins = sum(1 for s in high_conf_signals if s.result == "win")
        return wins / len(high_conf_signals)
