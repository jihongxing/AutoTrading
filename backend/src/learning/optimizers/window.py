"""
BTC 自动交易系统 — 窗口优化器

优化高交易窗口参数。
"""

from dataclasses import dataclass
from enum import Enum

from src.common.logging import get_logger

from ..analyzer import WindowAnalysis
from ..constants import SampleRequirements

logger = get_logger(__name__)


class WindowAction(str, Enum):
    """窗口调整动作"""
    RAISE_THRESHOLD = "raise_threshold"  # 提高阈值
    LOWER_THRESHOLD = "lower_threshold"  # 降低阈值
    INCREASE_MULTIPLIER = "increase_multiplier"  # 增加放大系数
    DECREASE_MULTIPLIER = "decrease_multiplier"  # 减少放大系数
    MAINTAIN = "maintain"


@dataclass
class WindowSuggestion:
    """窗口调整建议"""
    param_name: str  # threshold / multiplier
    current_value: float
    suggested_value: float
    action: WindowAction
    reason: str
    confidence: float
    requires_approval: bool


class WindowOptimizer:
    """
    窗口优化器
    
    优化：
    - 窗口判定阈值
    - 放大系数
    """
    
    def __init__(
        self,
        accuracy_target: float = 0.6,
        fp_threshold: float = 0.3,
        fn_threshold: float = 0.2,
    ):
        self.accuracy_target = accuracy_target
        self.fp_threshold = fp_threshold
        self.fn_threshold = fn_threshold
    
    def suggest_threshold_adjustment(
        self,
        analysis: WindowAnalysis,
        current_threshold: float,
    ) -> WindowSuggestion:
        """
        生成窗口阈值调整建议
        
        Args:
            analysis: 窗口分析结果
            current_threshold: 当前阈值
        
        Returns:
            窗口调整建议
        """
        if analysis.total_windows < SampleRequirements.MIN_TRADES_DAILY:
            return WindowSuggestion(
                param_name="window_threshold",
                current_value=current_threshold,
                suggested_value=current_threshold,
                action=WindowAction.MAINTAIN,
                reason="样本量不足",
                confidence=0.5,
                requires_approval=False,
            )
        
        # 基于假阳性和假阴性率判断
        if analysis.false_positive_rate > self.fp_threshold:
            # 假阳性过高，提高阈值
            action = WindowAction.RAISE_THRESHOLD
            adjustment = 0.05
            reason = f"假阳性率 {analysis.false_positive_rate:.2%} 过高，建议提高阈值"
        elif analysis.false_negative_rate > self.fn_threshold:
            # 假阴性过高，降低阈值
            action = WindowAction.LOWER_THRESHOLD
            adjustment = -0.05
            reason = f"假阴性率 {analysis.false_negative_rate:.2%} 过高，建议降低阈值"
        elif analysis.accuracy_rate < self.accuracy_target:
            # 准确率不达标
            action = WindowAction.RAISE_THRESHOLD
            adjustment = 0.03
            reason = f"准确率 {analysis.accuracy_rate:.2%} < {self.accuracy_target:.0%}，建议提高阈值"
        else:
            action = WindowAction.MAINTAIN
            adjustment = 0.0
            reason = "窗口阈值设置合理"
        
        new_value = current_threshold + adjustment
        new_value = max(0.5, min(0.9, new_value))
        
        return WindowSuggestion(
            param_name="window_threshold",
            current_value=current_threshold,
            suggested_value=new_value,
            action=action,
            reason=reason,
            confidence=min(1.0, analysis.total_windows / 50),
            requires_approval=abs(adjustment) > 0.05,
        )
    
    def suggest_multiplier_adjustment(
        self,
        analysis: WindowAnalysis,
        current_multiplier: float,
        avg_window_pnl: float,
        avg_normal_pnl: float,
    ) -> WindowSuggestion:
        """
        生成窗口放大系数调整建议
        
        Args:
            analysis: 窗口分析结果
            current_multiplier: 当前放大系数
            avg_window_pnl: 窗口期平均盈亏
            avg_normal_pnl: 正常期平均盈亏
        
        Returns:
            窗口调整建议
        """
        if analysis.total_windows < SampleRequirements.MIN_TRADES_DAILY:
            return WindowSuggestion(
                param_name="window_multiplier",
                current_value=current_multiplier,
                suggested_value=current_multiplier,
                action=WindowAction.MAINTAIN,
                reason="样本量不足",
                confidence=0.5,
                requires_approval=False,
            )
        
        # 比较窗口期和正常期表现
        if avg_normal_pnl == 0:
            performance_ratio = 1.0
        else:
            performance_ratio = avg_window_pnl / avg_normal_pnl
        
        if performance_ratio > 1.5 and analysis.accuracy_rate > 0.6:
            # 窗口期表现显著优于正常期，增加放大系数
            action = WindowAction.INCREASE_MULTIPLIER
            adjustment = 0.1
            reason = f"窗口期表现优于正常期 {performance_ratio:.2f}x，建议增加放大系数"
        elif performance_ratio < 1.0 or analysis.accuracy_rate < 0.5:
            # 窗口期表现不佳，减少放大系数
            action = WindowAction.DECREASE_MULTIPLIER
            adjustment = -0.1
            reason = f"窗口期表现不佳，建议减少放大系数"
        else:
            action = WindowAction.MAINTAIN
            adjustment = 0.0
            reason = "放大系数设置合理"
        
        new_value = current_multiplier + adjustment
        new_value = max(1.0, min(2.0, new_value))
        
        return WindowSuggestion(
            param_name="window_multiplier",
            current_value=current_multiplier,
            suggested_value=new_value,
            action=action,
            reason=reason,
            confidence=min(1.0, analysis.total_windows / 50),
            requires_approval=abs(adjustment) > 0.1,
        )
