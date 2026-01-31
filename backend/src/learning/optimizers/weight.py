"""
BTC 自动交易系统 — 权重优化器

优化证人权重。
"""

from dataclasses import dataclass
from enum import Enum

from src.common.logging import get_logger

from ..analyzer import WitnessPerformance
from ..constants import (
    MAX_DAILY_WEIGHT_CHANGE,
    WITNESS_WEIGHT_MAX,
    WITNESS_WEIGHT_MIN,
    WeightAdjustmentThresholds,
)

logger = get_logger(__name__)


class WeightAction(str, Enum):
    """权重调整动作"""
    INCREASE = "increase"
    DECREASE = "decrease"
    MAINTAIN = "maintain"
    MUTE = "mute"


@dataclass
class WeightSuggestion:
    """权重调整建议"""
    witness_id: str
    current_weight: float
    suggested_weight: float
    action: WeightAction
    reason: str
    confidence: float
    requires_approval: bool


class WeightOptimizer:
    """
    权重优化器
    
    根据证人表现调整权重：
    - 成功率 > 55% → +5%
    - 成功率 52-55% → 保持
    - 成功率 < 50% → -5%
    - 成功率 < 48% → Mute
    """
    
    def __init__(
        self,
        increase_threshold: float = WeightAdjustmentThresholds.INCREASE_THRESHOLD,
        maintain_min: float = WeightAdjustmentThresholds.MAINTAIN_MIN,
        decrease_threshold: float = WeightAdjustmentThresholds.DECREASE_THRESHOLD,
        mute_threshold: float = WeightAdjustmentThresholds.MUTE_THRESHOLD,
    ):
        self.increase_threshold = increase_threshold
        self.maintain_min = maintain_min
        self.decrease_threshold = decrease_threshold
        self.mute_threshold = mute_threshold
    
    def suggest_weight_adjustment(
        self,
        witness_id: str,
        performance: WitnessPerformance,
        current_weight: float,
    ) -> WeightSuggestion:
        """
        生成权重调整建议
        
        Args:
            witness_id: 证人 ID
            performance: 证人表现
            current_weight: 当前权重
        
        Returns:
            权重调整建议
        """
        # 样本量不足，保持
        if not performance.sample_sufficient:
            return WeightSuggestion(
                witness_id=witness_id,
                current_weight=current_weight,
                suggested_weight=current_weight,
                action=WeightAction.MAINTAIN,
                reason="样本量不足",
                confidence=0.5,
                requires_approval=False,
            )
        
        win_rate = performance.win_rate
        
        # 判断动作
        if win_rate >= self.increase_threshold:
            action = WeightAction.INCREASE
            adjustment = WeightAdjustmentThresholds.INCREASE_AMOUNT
            reason = f"胜率 {win_rate:.2%} >= {self.increase_threshold:.0%}"
        elif win_rate >= self.maintain_min:
            action = WeightAction.MAINTAIN
            adjustment = 0.0
            reason = f"胜率 {win_rate:.2%} 在正常范围"
        elif win_rate >= self.mute_threshold:
            action = WeightAction.DECREASE
            adjustment = -WeightAdjustmentThresholds.DECREASE_AMOUNT
            reason = f"胜率 {win_rate:.2%} < {self.decrease_threshold:.0%}"
        else:
            action = WeightAction.MUTE
            adjustment = 0.0
            reason = f"胜率 {win_rate:.2%} < {self.mute_threshold:.0%}，建议静默"
        
        # 计算新权重
        new_weight = current_weight + adjustment
        
        # 边界检查
        new_weight = self._apply_bounds(new_weight)
        
        # 检查单日最大调整幅度
        actual_change = abs(new_weight - current_weight)
        if actual_change > MAX_DAILY_WEIGHT_CHANGE:
            new_weight = current_weight + (MAX_DAILY_WEIGHT_CHANGE if adjustment > 0 else -MAX_DAILY_WEIGHT_CHANGE)
        
        # 判断是否需要审批
        requires_approval = actual_change > 0.1  # 变化超过 10% 需要审批
        
        # 计算置信度
        confidence = self._calculate_confidence(performance)
        
        logger.info(
            f"权重建议: {witness_id}, {action.value}, {current_weight:.2f} -> {new_weight:.2f}",
            extra={"witness_id": witness_id, "action": action.value, "new_weight": new_weight},
        )
        
        return WeightSuggestion(
            witness_id=witness_id,
            current_weight=current_weight,
            suggested_weight=new_weight,
            action=action,
            reason=reason,
            confidence=confidence,
            requires_approval=requires_approval,
        )
    
    def _apply_bounds(self, weight: float) -> float:
        """应用边界约束"""
        return max(WITNESS_WEIGHT_MIN, min(WITNESS_WEIGHT_MAX, weight))
    
    def _calculate_confidence(self, performance: WitnessPerformance) -> float:
        """计算建议置信度"""
        # 基于样本量和置信度准确性
        sample_factor = min(1.0, performance.total_signals / 100)
        accuracy_factor = performance.confidence_accuracy
        
        return 0.5 + sample_factor * 0.25 + accuracy_factor * 0.25
