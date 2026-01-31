"""
BTC 自动交易系统 — 仓位优化器

优化仓位系数和默认仓位比例。
"""

from dataclasses import dataclass
from enum import Enum

from src.common.logging import get_logger

from ..constants import (
    DEFAULT_POSITION_MAX,
    DEFAULT_POSITION_MIN,
    POSITION_MULTIPLIER_MAX,
    POSITION_MULTIPLIER_MIN,
    SampleRequirements,
)
from ..statistics import PnLStatistics

logger = get_logger(__name__)


class PositionAction(str, Enum):
    """仓位调整动作"""
    INCREASE = "increase"
    DECREASE = "decrease"
    MAINTAIN = "maintain"


@dataclass
class PositionSuggestion:
    """仓位调整建议"""
    param_name: str  # multiplier / default_ratio
    current_value: float
    suggested_value: float
    action: PositionAction
    reason: str
    confidence: float
    requires_approval: bool


class PositionOptimizer:
    """
    仓位优化器
    
    优化：
    - 仓位放大系数（0.5-1.5）
    - 默认仓位比例（1%-3%）
    """
    
    def __init__(
        self,
        win_rate_threshold: float = 0.55,
        sharpe_threshold: float = 1.0,
    ):
        self.win_rate_threshold = win_rate_threshold
        self.sharpe_threshold = sharpe_threshold
    
    def suggest_multiplier_adjustment(
        self,
        stats: PnLStatistics,
        current_multiplier: float,
        sharpe_ratio: float,
    ) -> PositionSuggestion:
        """
        生成仓位放大系数调整建议
        
        Args:
            stats: 盈亏统计
            current_multiplier: 当前放大系数
            sharpe_ratio: 夏普比率
        
        Returns:
            仓位调整建议
        """
        # 样本量检查
        if stats.total_trades < SampleRequirements.MIN_TRADES_FOR_POSITION:
            return PositionSuggestion(
                param_name="position_multiplier",
                current_value=current_multiplier,
                suggested_value=current_multiplier,
                action=PositionAction.MAINTAIN,
                reason="样本量不足",
                confidence=0.5,
                requires_approval=False,
            )
        
        # 判断调整方向
        if stats.win_rate >= self.win_rate_threshold and sharpe_ratio >= self.sharpe_threshold:
            # 表现优秀，可以增加仓位
            action = PositionAction.INCREASE
            adjustment = 0.1
            reason = f"胜率 {stats.win_rate:.2%}, Sharpe {sharpe_ratio:.2f} 表现优秀"
        elif stats.win_rate < 0.48 or sharpe_ratio < 0.5:
            # 表现不佳，减少仓位
            action = PositionAction.DECREASE
            adjustment = -0.1
            reason = f"胜率 {stats.win_rate:.2%}, Sharpe {sharpe_ratio:.2f} 表现不佳"
        else:
            action = PositionAction.MAINTAIN
            adjustment = 0.0
            reason = "表现正常，保持当前仓位"
        
        # 计算新值
        new_value = current_multiplier + adjustment
        new_value = max(POSITION_MULTIPLIER_MIN, min(POSITION_MULTIPLIER_MAX, new_value))
        
        # 判断是否需要审批
        change_pct = abs(new_value - current_multiplier) / current_multiplier
        requires_approval = change_pct > 0.2
        
        return PositionSuggestion(
            param_name="position_multiplier",
            current_value=current_multiplier,
            suggested_value=new_value,
            action=action,
            reason=reason,
            confidence=min(1.0, stats.total_trades / 100),
            requires_approval=requires_approval,
        )
    
    def suggest_default_ratio_adjustment(
        self,
        stats: PnLStatistics,
        current_ratio: float,
        max_drawdown_pct: float,
    ) -> PositionSuggestion:
        """
        生成默认仓位比例调整建议
        
        Args:
            stats: 盈亏统计
            current_ratio: 当前默认仓位比例
            max_drawdown_pct: 最大回撤百分比
        
        Returns:
            仓位调整建议
        """
        # 样本量检查
        if stats.total_trades < SampleRequirements.MIN_TRADES_FOR_POSITION:
            return PositionSuggestion(
                param_name="default_position_ratio",
                current_value=current_ratio,
                suggested_value=current_ratio,
                action=PositionAction.MAINTAIN,
                reason="样本量不足",
                confidence=0.5,
                requires_approval=False,
            )
        
        # 基于回撤和盈利因子判断
        if max_drawdown_pct > 0.15:
            # 回撤过大，减少仓位
            action = PositionAction.DECREASE
            adjustment = -0.005
            reason = f"最大回撤 {max_drawdown_pct:.2%} 过大"
        elif stats.profit_factor > 1.5 and max_drawdown_pct < 0.10:
            # 盈利因子高且回撤小，可以增加
            action = PositionAction.INCREASE
            adjustment = 0.005
            reason = f"盈利因子 {stats.profit_factor:.2f}, 回撤 {max_drawdown_pct:.2%} 表现优秀"
        else:
            action = PositionAction.MAINTAIN
            adjustment = 0.0
            reason = "表现正常，保持当前比例"
        
        # 计算新值
        new_value = current_ratio + adjustment
        new_value = max(DEFAULT_POSITION_MIN, min(DEFAULT_POSITION_MAX, new_value))
        
        return PositionSuggestion(
            param_name="default_position_ratio",
            current_value=current_ratio,
            suggested_value=new_value,
            action=action,
            reason=reason,
            confidence=min(1.0, stats.total_trades / 100),
            requires_approval=abs(adjustment) > 0,
        )
