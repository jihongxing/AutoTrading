"""
BTC 自动交易系统 — 证人健康度管理

管理证人健康度计算、等级判定和自动 Mute/Ban。
"""

from dataclasses import dataclass
from datetime import datetime

from src.common.constants import LearningBounds
from src.common.enums import HealthGrade, WitnessStatus, WitnessTier
from src.common.logging import get_logger
from src.common.models import WitnessHealth
from src.common.utils import utc_now

from .base import BaseStrategy

logger = get_logger(__name__)


@dataclass
class TradeResult:
    """交易结果"""
    strategy_id: str
    is_win: bool
    pnl: float
    timestamp: datetime


class HealthManager:
    """
    证人健康度管理器
    
    健康度等级：
    - A: ≥55%, 权重 +5%
    - B: 52-55%, 保持
    - C: 30-52%, 权重 -5%
    - D: <30%, 自动 Mute
    """
    
    MIN_SAMPLE_SIZE = 50  # 最小样本量
    
    def __init__(self):
        self._health_data: dict[str, WitnessHealth] = {}
        self._trade_history: dict[str, list[TradeResult]] = {}
    
    def initialize_health(self, witness: BaseStrategy) -> WitnessHealth:
        """初始化证人健康度"""
        health = WitnessHealth(
            witness_id=witness.strategy_id,
            tier=witness.tier,
            status=WitnessStatus.ACTIVE,
            grade=HealthGrade.B,
            win_rate=0.5,
            sample_count=0,
            weight=0.5,
        )
        self._health_data[witness.strategy_id] = health
        self._trade_history[witness.strategy_id] = []
        return health
    
    def update_health(
        self,
        strategy_id: str,
        trade_result: TradeResult,
    ) -> WitnessHealth | None:
        """
        更新证人健康度
        
        Args:
            strategy_id: 策略 ID
            trade_result: 交易结果
        
        Returns:
            更新后的健康度
        """
        if strategy_id not in self._health_data:
            logger.warning(f"证人未初始化: {strategy_id}")
            return None
        
        # 记录交易结果
        if strategy_id not in self._trade_history:
            self._trade_history[strategy_id] = []
        self._trade_history[strategy_id].append(trade_result)
        
        # 计算新的健康度
        history = self._trade_history[strategy_id]
        sample_count = len(history)
        wins = sum(1 for t in history if t.is_win)
        win_rate = wins / sample_count if sample_count > 0 else 0.5
        
        # 计算 Sharpe（简化版）
        pnls = [t.pnl for t in history]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        
        # 计算最大回撤（简化版）
        cumulative = 0
        peak = 0
        max_dd = 0
        for t in history:
            cumulative += t.pnl
            peak = max(peak, cumulative)
            dd = (peak - cumulative) / peak if peak > 0 else 0
            max_dd = max(max_dd, min(dd, 1.0))  # 限制在 0-1 范围
        
        # 判定等级
        grade = self._calculate_grade(win_rate, sample_count)
        
        # 计算权重调整
        old_health = self._health_data[strategy_id]
        new_weight = self._adjust_weight(old_health.weight, grade)
        
        # 判定状态
        status = self._determine_status(grade, sample_count)
        
        # 更新健康度
        new_health = WitnessHealth(
            witness_id=strategy_id,
            tier=old_health.tier,
            status=status,
            grade=grade,
            win_rate=win_rate,
            sample_count=sample_count,
            sharpe_ratio=avg_pnl,
            max_drawdown=max_dd,
            weight=new_weight,
        )
        
        self._health_data[strategy_id] = new_health
        
        logger.info(
            f"健康度更新: {strategy_id}, 胜率: {win_rate:.2%}, 等级: {grade.value}",
            extra={"strategy_id": strategy_id, "win_rate": win_rate, "grade": grade.value},
        )
        
        return new_health
    
    def get_health(self, strategy_id: str) -> WitnessHealth | None:
        """获取证人健康度"""
        return self._health_data.get(strategy_id)
    
    def check_auto_mute(self, strategy_id: str) -> bool:
        """
        检查是否需要自动 Mute
        
        Returns:
            是否需要 Mute
        """
        health = self._health_data.get(strategy_id)
        if not health:
            return False
        
        # D 等级且样本量足够时自动 Mute
        if health.grade == HealthGrade.D and health.sample_count >= self.MIN_SAMPLE_SIZE:
            logger.warning(f"证人自动 Mute: {strategy_id}, 等级: D")
            return True
        
        return False
    
    def _calculate_grade(self, win_rate: float, sample_count: int) -> HealthGrade:
        """计算健康度等级"""
        if sample_count < self.MIN_SAMPLE_SIZE:
            return HealthGrade.B  # 样本不足，保持 B
        
        if win_rate >= 0.55:
            return HealthGrade.A
        elif win_rate >= 0.52:
            return HealthGrade.B
        elif win_rate >= 0.30:
            return HealthGrade.C
        else:
            return HealthGrade.D
    
    def _adjust_weight(self, current_weight: float, grade: HealthGrade) -> float:
        """调整权重"""
        adjustment = 0.0
        
        if grade == HealthGrade.A:
            adjustment = 0.05
        elif grade == HealthGrade.C:
            adjustment = -0.05
        elif grade == HealthGrade.D:
            adjustment = -0.10
        
        new_weight = current_weight + adjustment
        
        # 限制在边界内
        return max(
            LearningBounds.WITNESS_WEIGHT_MIN,
            min(LearningBounds.WITNESS_WEIGHT_MAX, new_weight)
        )
    
    def _determine_status(self, grade: HealthGrade, sample_count: int) -> WitnessStatus:
        """判定状态"""
        if sample_count < self.MIN_SAMPLE_SIZE:
            return WitnessStatus.ACTIVE
        
        if grade == HealthGrade.D:
            return WitnessStatus.MUTED
        
        return WitnessStatus.ACTIVE
