"""
BTC 自动交易系统 — 止盈止损优化器

优化止损和止盈参数。
"""

from dataclasses import dataclass
from enum import Enum

from src.common.logging import get_logger

from ..collector import TradeData
from ..constants import STOP_ADJUSTMENT_MAX, STOP_ADJUSTMENT_MIN, SampleRequirements

logger = get_logger(__name__)


class StopAction(str, Enum):
    """止损止盈调整动作"""
    TIGHTEN = "tighten"  # 收紧
    LOOSEN = "loosen"  # 放宽
    MAINTAIN = "maintain"


@dataclass
class StopSuggestion:
    """止损止盈调整建议"""
    param_name: str  # stop_loss / take_profit
    current_value: float
    suggested_value: float
    action: StopAction
    reason: str
    confidence: float
    requires_approval: bool


class StopOptimizer:
    """
    止盈止损优化器
    
    优化：
    - 止损微调（±0.5%）
    - 止盈微调（±0.5%）
    """
    
    def __init__(
        self,
        min_adjustment: float = STOP_ADJUSTMENT_MIN,
        max_adjustment: float = STOP_ADJUSTMENT_MAX,
    ):
        self.min_adjustment = min_adjustment
        self.max_adjustment = max_adjustment
    
    def suggest_stop_loss_adjustment(
        self,
        trades: list[TradeData],
        current_stop_loss: float,
    ) -> StopSuggestion:
        """
        生成止损调整建议
        
        Args:
            trades: 交易数据列表
            current_stop_loss: 当前止损比例
        
        Returns:
            止损调整建议
        """
        if len(trades) < SampleRequirements.MIN_TRADES_FOR_STOP:
            return StopSuggestion(
                param_name="stop_loss",
                current_value=current_stop_loss,
                suggested_value=current_stop_loss,
                action=StopAction.MAINTAIN,
                reason="样本量不足",
                confidence=0.5,
                requires_approval=False,
            )
        
        # 分析止损触发情况
        stop_triggered = [t for t in trades if not t.is_win and t.duration_seconds < 600]
        quick_recovery = [t for t in trades if t.is_win and t.duration_seconds < 1800]
        
        stop_rate = len(stop_triggered) / len(trades)
        recovery_rate = len(quick_recovery) / len(trades)
        
        # 判断调整方向
        if stop_rate > 0.3:
            # 止损触发过于频繁，可能止损太紧
            action = StopAction.LOOSEN
            adjustment = 0.002
            reason = f"止损触发率 {stop_rate:.2%} 过高，建议放宽"
        elif stop_rate < 0.1 and recovery_rate > 0.2:
            # 止损触发少但快速恢复多，可能止损太松
            action = StopAction.TIGHTEN
            adjustment = -0.002
            reason = f"止损触发率 {stop_rate:.2%} 较低，快速恢复率 {recovery_rate:.2%}，建议收紧"
        else:
            action = StopAction.MAINTAIN
            adjustment = 0.0
            reason = "止损设置合理"
        
        # 应用边界
        new_value = current_stop_loss + adjustment
        new_value = max(
            current_stop_loss + self.min_adjustment,
            min(current_stop_loss + self.max_adjustment, new_value)
        )
        
        return StopSuggestion(
            param_name="stop_loss",
            current_value=current_stop_loss,
            suggested_value=new_value,
            action=action,
            reason=reason,
            confidence=min(1.0, len(trades) / 200),
            requires_approval=abs(adjustment) > 0,
        )
    
    def suggest_take_profit_adjustment(
        self,
        trades: list[TradeData],
        current_take_profit: float,
    ) -> StopSuggestion:
        """
        生成止盈调整建议
        
        Args:
            trades: 交易数据列表
            current_take_profit: 当前止盈比例
        
        Returns:
            止盈调整建议
        """
        if len(trades) < SampleRequirements.MIN_TRADES_FOR_STOP:
            return StopSuggestion(
                param_name="take_profit",
                current_value=current_take_profit,
                suggested_value=current_take_profit,
                action=StopAction.MAINTAIN,
                reason="样本量不足",
                confidence=0.5,
                requires_approval=False,
            )
        
        # 分析盈利交易
        winning_trades = [t for t in trades if t.is_win]
        
        if not winning_trades:
            return StopSuggestion(
                param_name="take_profit",
                current_value=current_take_profit,
                suggested_value=current_take_profit,
                action=StopAction.MAINTAIN,
                reason="无盈利交易数据",
                confidence=0.5,
                requires_approval=False,
            )
        
        # 计算平均盈利比例
        avg_profit_pct = sum(
            t.pnl / (t.entry_price * t.quantity) for t in winning_trades
        ) / len(winning_trades)
        
        # 判断调整方向
        if avg_profit_pct > current_take_profit * 1.2:
            # 实际盈利超过止盈设置，可以放宽
            action = StopAction.LOOSEN
            adjustment = 0.002
            reason = f"平均盈利 {avg_profit_pct:.2%} > 止盈 {current_take_profit:.2%}，建议放宽"
        elif avg_profit_pct < current_take_profit * 0.8:
            # 实际盈利低于止盈设置，可能需要收紧
            action = StopAction.TIGHTEN
            adjustment = -0.002
            reason = f"平均盈利 {avg_profit_pct:.2%} < 止盈 {current_take_profit:.2%}，建议收紧"
        else:
            action = StopAction.MAINTAIN
            adjustment = 0.0
            reason = "止盈设置合理"
        
        # 应用边界
        new_value = current_take_profit + adjustment
        new_value = max(
            current_take_profit + self.min_adjustment,
            min(current_take_profit + self.max_adjustment, new_value)
        )
        
        return StopSuggestion(
            param_name="take_profit",
            current_value=current_take_profit,
            suggested_value=new_value,
            action=action,
            reason=reason,
            confidence=min(1.0, len(trades) / 200),
            requires_approval=abs(adjustment) > 0,
        )
