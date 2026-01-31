"""
BTC 自动交易系统 — 学习引擎

整合所有优化器，调度学习任务，生成学习报告。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.common.logging import get_logger
from src.common.utils import utc_now

from .analyzer import PostTradeAnalyzer, WitnessPerformance
from .collector import LearningDataCollector, SignalData, TradeData
from .constants import FORBIDDEN_PARAMS, SampleRequirements
from .optimizers import (
    PositionOptimizer,
    PositionSuggestion,
    StopOptimizer,
    StopSuggestion,
    WeightOptimizer,
    WeightSuggestion,
    WindowOptimizer,
    WindowSuggestion,
)
from .statistics import StatisticsAnalyzer

logger = get_logger(__name__)


@dataclass
class Suggestion:
    """通用建议"""
    param_name: str
    current_value: float
    suggested_value: float
    action: str
    reason: str
    confidence: float
    requires_approval: bool


@dataclass
class LearningReport:
    """学习报告"""
    period: str  # daily/weekly
    timestamp: datetime
    start_time: datetime
    end_time: datetime
    
    # 统计
    total_trades: int
    win_rate: float
    avg_pnl: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    
    # 建议
    weight_suggestions: list[WeightSuggestion] = field(default_factory=list)
    position_suggestions: list[PositionSuggestion] = field(default_factory=list)
    stop_suggestions: list[StopSuggestion] = field(default_factory=list)
    window_suggestions: list[WindowSuggestion] = field(default_factory=list)
    
    # 需要审批的调整
    requires_approval: list[Suggestion] = field(default_factory=list)
    
    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)


class LearningEngine:
    """
    学习引擎
    
    职责：
    1. 整合所有优化器
    2. 调度学习任务
    3. 生成学习报告
    4. 应用建议（需审批）
    """
    
    def __init__(
        self,
        collector: LearningDataCollector,
        analyzer: PostTradeAnalyzer | None = None,
        statistics: StatisticsAnalyzer | None = None,
    ):
        self.collector = collector
        self.analyzer = analyzer or PostTradeAnalyzer()
        self.statistics = statistics or StatisticsAnalyzer()
        
        # 优化器
        self.weight_optimizer = WeightOptimizer()
        self.position_optimizer = PositionOptimizer()
        self.stop_optimizer = StopOptimizer()
        self.window_optimizer = WindowOptimizer()
        
        # 当前参数（从存储加载）
        self._current_params: dict[str, float] = {
            "position_multiplier": 1.0,
            "default_position_ratio": 0.02,
            "stop_loss": 0.02,
            "take_profit": 0.03,
            "window_threshold": 0.6,
            "window_multiplier": 1.5,
        }
        
        # 证人权重
        self._witness_weights: dict[str, float] = {}
    
    async def run_daily_learning(self) -> LearningReport:
        """
        运行每日学习
        
        Returns:
            学习报告
        """
        now = utc_now()
        start_time = now - timedelta(days=1)
        end_time = now
        
        logger.info("开始每日学习", extra={"start": start_time.isoformat()})
        
        # 收集数据
        trades = await self.collector.collect_trade_data(start_time, end_time)
        signals = await self.collector.collect_signal_data(start_time, end_time)
        
        # 检查样本量
        if len(trades) < SampleRequirements.MIN_TRADES_DAILY:
            logger.warning(f"每日交易数 {len(trades)} 不足，跳过学习")
            return self._create_empty_report("daily", start_time, end_time)
        
        # 计算统计
        pnl_stats = self.statistics.calculate_pnl_statistics(trades)
        dd_stats = self.statistics.calculate_drawdown_statistics(trades)
        sharpe = self.statistics.calculate_sharpe_ratio(trades)
        
        # 生成建议
        weight_suggestions = await self._generate_weight_suggestions(trades, signals)
        position_suggestions = await self._generate_position_suggestions(pnl_stats, sharpe, dd_stats.max_drawdown_pct)
        
        # 收集需要审批的建议
        requires_approval = self._collect_approval_required(
            weight_suggestions, position_suggestions, [], []
        )
        
        report = LearningReport(
            period="daily",
            timestamp=now,
            start_time=start_time,
            end_time=end_time,
            total_trades=pnl_stats.total_trades,
            win_rate=pnl_stats.win_rate,
            avg_pnl=pnl_stats.avg_pnl,
            total_pnl=pnl_stats.total_pnl,
            max_drawdown=dd_stats.max_drawdown_pct,
            sharpe_ratio=sharpe,
            weight_suggestions=weight_suggestions,
            position_suggestions=position_suggestions,
            requires_approval=requires_approval,
        )
        
        logger.info(
            f"每日学习完成: 交易数={pnl_stats.total_trades}, 胜率={pnl_stats.win_rate:.2%}",
            extra={"trades": pnl_stats.total_trades, "win_rate": pnl_stats.win_rate},
        )
        
        return report
    
    async def run_weekly_learning(self) -> LearningReport:
        """
        运行每周学习
        
        Returns:
            学习报告
        """
        now = utc_now()
        start_time = now - timedelta(days=7)
        end_time = now
        
        logger.info("开始每周学习", extra={"start": start_time.isoformat()})
        
        # 收集数据
        trades = await self.collector.collect_trade_data(start_time, end_time)
        signals = await self.collector.collect_signal_data(start_time, end_time)
        
        # 检查样本量
        if len(trades) < SampleRequirements.MIN_TRADES_WEEKLY:
            logger.warning(f"每周交易数 {len(trades)} 不足，跳过学习")
            return self._create_empty_report("weekly", start_time, end_time)
        
        # 计算统计
        pnl_stats = self.statistics.calculate_pnl_statistics(trades)
        dd_stats = self.statistics.calculate_drawdown_statistics(trades)
        sharpe = self.statistics.calculate_sharpe_ratio(trades)
        
        # 生成所有建议
        weight_suggestions = await self._generate_weight_suggestions(trades, signals)
        position_suggestions = await self._generate_position_suggestions(pnl_stats, sharpe, dd_stats.max_drawdown_pct)
        stop_suggestions = await self._generate_stop_suggestions(trades)
        window_suggestions = await self._generate_window_suggestions(signals, trades)
        
        # 收集需要审批的建议
        requires_approval = self._collect_approval_required(
            weight_suggestions, position_suggestions, stop_suggestions, window_suggestions
        )
        
        report = LearningReport(
            period="weekly",
            timestamp=now,
            start_time=start_time,
            end_time=end_time,
            total_trades=pnl_stats.total_trades,
            win_rate=pnl_stats.win_rate,
            avg_pnl=pnl_stats.avg_pnl,
            total_pnl=pnl_stats.total_pnl,
            max_drawdown=dd_stats.max_drawdown_pct,
            sharpe_ratio=sharpe,
            weight_suggestions=weight_suggestions,
            position_suggestions=position_suggestions,
            stop_suggestions=stop_suggestions,
            window_suggestions=window_suggestions,
            requires_approval=requires_approval,
        )
        
        logger.info(
            f"每周学习完成: 交易数={pnl_stats.total_trades}, 胜率={pnl_stats.win_rate:.2%}",
            extra={"trades": pnl_stats.total_trades, "win_rate": pnl_stats.win_rate},
        )
        
        return report
    
    async def apply_suggestions(
        self,
        suggestions: list[Suggestion],
        approved: bool = False,
    ) -> dict[str, Any]:
        """
        应用建议
        
        Args:
            suggestions: 建议列表
            approved: 是否已审批
        
        Returns:
            应用结果
        """
        applied = []
        skipped = []
        
        for suggestion in suggestions:
            # 检查是否为禁止参数
            if suggestion.param_name in FORBIDDEN_PARAMS:
                logger.warning(f"尝试修改禁止参数: {suggestion.param_name}")
                skipped.append(suggestion.param_name)
                continue
            
            # 检查是否需要审批
            if suggestion.requires_approval and not approved:
                logger.info(f"建议需要审批: {suggestion.param_name}")
                skipped.append(suggestion.param_name)
                continue
            
            # 应用建议
            self._current_params[suggestion.param_name] = suggestion.suggested_value
            applied.append(suggestion.param_name)
            
            logger.info(
                f"应用建议: {suggestion.param_name} = {suggestion.suggested_value}",
                extra={"param": suggestion.param_name, "value": suggestion.suggested_value},
            )
        
        return {"applied": applied, "skipped": skipped}
    
    def set_witness_weight(self, witness_id: str, weight: float) -> None:
        """设置证人权重"""
        self._witness_weights[witness_id] = weight
    
    def get_witness_weight(self, witness_id: str) -> float:
        """获取证人权重"""
        return self._witness_weights.get(witness_id, 0.5)
    
    async def optimize_weights(self, weight_manager: Any) -> dict[str, float]:
        """
        优化证人权重（每周学习任务）
        
        基于历史绩效计算 learning_factor，调用 WeightManager.set_learning_factor()
        
        Args:
            weight_manager: WeightManager 实例
        
        Returns:
            更新的 learning_factor 字典
        """
        now = utc_now()
        start_time = now - timedelta(days=7)
        end_time = now
        
        logger.info("开始权重优化", extra={"start": start_time.isoformat()})
        
        # 收集数据
        trades = await self.collector.collect_trade_data(start_time, end_time)
        signals = await self.collector.collect_signal_data(start_time, end_time)
        
        if len(trades) < SampleRequirements.MIN_TRADES_WEEKLY:
            logger.warning("样本不足，跳过权重优化")
            return {}
        
        # 获取所有证人 ID
        witness_ids = set()
        for trade in trades:
            witness_ids.update(trade.witness_ids)
        
        updated = {}
        
        for witness_id in witness_ids:
            # 分析证人绩效
            performance = self.analyzer.analyze_witness_performance(
                witness_id, trades, signals
            )
            
            # 计算 learning_factor
            # 基于胜率和 Sharpe 比率
            base_factor = 1.0
            
            if performance.win_rate >= 0.55:
                base_factor = 1.1
            elif performance.win_rate >= 0.52:
                base_factor = 1.0
            elif performance.win_rate >= 0.48:
                base_factor = 0.95
            else:
                base_factor = 0.9
            
            # Sharpe 调整
            if performance.sharpe_ratio > 1.5:
                base_factor *= 1.05
            elif performance.sharpe_ratio < 0.5:
                base_factor *= 0.95
            
            # 限制在 0.8-1.2 范围
            learning_factor = max(0.8, min(1.2, base_factor))
            
            # 更新 WeightManager
            weight_manager.set_learning_factor(witness_id, learning_factor)
            updated[witness_id] = learning_factor
            
            logger.info(
                f"权重优化: {witness_id}, learning_factor={learning_factor:.3f}",
                extra={"witness_id": witness_id, "learning_factor": learning_factor},
            )
        
        return updated
    
    async def _generate_weight_suggestions(
        self,
        trades: list[TradeData],
        signals: list[SignalData],
    ) -> list[WeightSuggestion]:
        """生成权重调整建议"""
        suggestions = []
        
        # 获取所有证人 ID
        witness_ids = set()
        for trade in trades:
            witness_ids.update(trade.witness_ids)
        
        for witness_id in witness_ids:
            performance = self.analyzer.analyze_witness_performance(
                witness_id, trades, signals
            )
            current_weight = self.get_witness_weight(witness_id)
            
            suggestion = self.weight_optimizer.suggest_weight_adjustment(
                witness_id, performance, current_weight
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    async def _generate_position_suggestions(
        self,
        stats: Any,
        sharpe: float,
        max_dd: float,
    ) -> list[PositionSuggestion]:
        """生成仓位调整建议"""
        suggestions = []
        
        # 仓位放大系数
        multiplier_suggestion = self.position_optimizer.suggest_multiplier_adjustment(
            stats,
            self._current_params["position_multiplier"],
            sharpe,
        )
        suggestions.append(multiplier_suggestion)
        
        # 默认仓位比例
        ratio_suggestion = self.position_optimizer.suggest_default_ratio_adjustment(
            stats,
            self._current_params["default_position_ratio"],
            max_dd,
        )
        suggestions.append(ratio_suggestion)
        
        return suggestions
    
    async def _generate_stop_suggestions(
        self,
        trades: list[TradeData],
    ) -> list[StopSuggestion]:
        """生成止损止盈调整建议"""
        suggestions = []
        
        # 止损
        sl_suggestion = self.stop_optimizer.suggest_stop_loss_adjustment(
            trades,
            self._current_params["stop_loss"],
        )
        suggestions.append(sl_suggestion)
        
        # 止盈
        tp_suggestion = self.stop_optimizer.suggest_take_profit_adjustment(
            trades,
            self._current_params["take_profit"],
        )
        suggestions.append(tp_suggestion)
        
        return suggestions
    
    async def _generate_window_suggestions(
        self,
        signals: list[SignalData],
        trades: list[TradeData],
    ) -> list[WindowSuggestion]:
        """生成窗口调整建议"""
        suggestions = []
        
        # 分析窗口准确率
        window_analysis = self.analyzer.analyze_window_accuracy(signals)
        
        # 阈值
        threshold_suggestion = self.window_optimizer.suggest_threshold_adjustment(
            window_analysis,
            self._current_params["window_threshold"],
        )
        suggestions.append(threshold_suggestion)
        
        # 放大系数
        # 简化：使用平均盈亏
        avg_pnl = sum(t.pnl for t in trades) / len(trades) if trades else 0
        multiplier_suggestion = self.window_optimizer.suggest_multiplier_adjustment(
            window_analysis,
            self._current_params["window_multiplier"],
            avg_pnl,
            avg_pnl * 0.8,  # 假设正常期盈亏略低
        )
        suggestions.append(multiplier_suggestion)
        
        return suggestions
    
    def _collect_approval_required(
        self,
        weight: list[WeightSuggestion],
        position: list[PositionSuggestion],
        stop: list[StopSuggestion],
        window: list[WindowSuggestion],
    ) -> list[Suggestion]:
        """收集需要审批的建议"""
        result = []
        
        for s in weight:
            if s.requires_approval:
                result.append(Suggestion(
                    param_name=f"weight_{s.witness_id}",
                    current_value=s.current_weight,
                    suggested_value=s.suggested_weight,
                    action=s.action.value,
                    reason=s.reason,
                    confidence=s.confidence,
                    requires_approval=True,
                ))
        
        for s in position:
            if s.requires_approval:
                result.append(Suggestion(
                    param_name=s.param_name,
                    current_value=s.current_value,
                    suggested_value=s.suggested_value,
                    action=s.action.value,
                    reason=s.reason,
                    confidence=s.confidence,
                    requires_approval=True,
                ))
        
        for s in stop:
            if s.requires_approval:
                result.append(Suggestion(
                    param_name=s.param_name,
                    current_value=s.current_value,
                    suggested_value=s.suggested_value,
                    action=s.action.value,
                    reason=s.reason,
                    confidence=s.confidence,
                    requires_approval=True,
                ))
        
        for s in window:
            if s.requires_approval:
                result.append(Suggestion(
                    param_name=s.param_name,
                    current_value=s.current_value,
                    suggested_value=s.suggested_value,
                    action=s.action.value,
                    reason=s.reason,
                    confidence=s.confidence,
                    requires_approval=True,
                ))
        
        return result
    
    def _create_empty_report(
        self,
        period: str,
        start_time: datetime,
        end_time: datetime,
    ) -> LearningReport:
        """创建空报告"""
        return LearningReport(
            period=period,
            timestamp=utc_now(),
            start_time=start_time,
            end_time=end_time,
            total_trades=0,
            win_rate=0.0,
            avg_pnl=0.0,
            total_pnl=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            metadata={"reason": "insufficient_samples"},
        )
