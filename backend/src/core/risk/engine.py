"""
BTC 自动交易系统 — 风控引擎

聚合所有风险检查器，提供统一的风控接口。
"""

from collections import defaultdict
from datetime import datetime

from src.common.enums import RiskLevel
from src.common.logging import get_logger
from src.common.models import RiskCheckResult, RiskEvent
from src.common.utils import utc_now

from .account_risk import AccountRiskChecker
from .base import RiskChecker, RiskContext
from .behavior_risk import BehaviorRiskChecker
from .execution_risk import ExecutionRiskChecker
from .regime_risk import RegimeRiskChecker
from .system_risk import SystemRiskChecker

logger = get_logger(__name__)


class WitnessCorrelationCalculator:
    """
    证人相关性计算器
    
    计算证人之间的相关性，避免高度相关的证人同时触发导致风险集中。
    """
    
    # 相关性阈值：超过此值认为高度相关
    HIGH_CORRELATION_THRESHOLD = 0.7
    # 最大允许的高相关证人数
    MAX_CORRELATED_WITNESSES = 2
    
    def __init__(self):
        # 证人信号历史：{witness_id: [(timestamp, direction, result)]}
        self._signal_history: dict[str, list[tuple[datetime, str, bool]]] = defaultdict(list)
        # 缓存的相关性矩阵
        self._correlation_matrix: dict[tuple[str, str], float] = {}
        self._last_update: datetime | None = None
    
    def record_signal(
        self,
        witness_id: str,
        timestamp: datetime,
        direction: str,
        result: bool,
    ) -> None:
        """记录证人信号结果"""
        self._signal_history[witness_id].append((timestamp, direction, result))
        # 保留最近 200 条记录
        if len(self._signal_history[witness_id]) > 200:
            self._signal_history[witness_id] = self._signal_history[witness_id][-200:]
    
    def calculate_correlation(self, witness_a: str, witness_b: str) -> float:
        """
        计算两个证人之间的相关性
        
        基于信号方向和结果的一致性计算。
        """
        history_a = self._signal_history.get(witness_a, [])
        history_b = self._signal_history.get(witness_b, [])
        
        if len(history_a) < 20 or len(history_b) < 20:
            return 0.0  # 样本不足，返回无相关
        
        # 找到时间重叠的信号
        matches = 0
        total = 0
        
        # 简化：按时间窗口匹配（1小时内）
        for ts_a, dir_a, res_a in history_a[-50:]:
            for ts_b, dir_b, res_b in history_b[-50:]:
                time_diff = abs((ts_a - ts_b).total_seconds())
                if time_diff < 3600:  # 1小时内
                    total += 1
                    # 方向相同且结果相同
                    if dir_a == dir_b and res_a == res_b:
                        matches += 1
        
        if total == 0:
            return 0.0
        
        return matches / total
    
    def check_correlation_risk(
        self,
        active_witnesses: list[str],
    ) -> tuple[bool, str, list[tuple[str, str, float]]]:
        """
        检查证人相关性风险
        
        Args:
            active_witnesses: 当前激活的证人列表
        
        Returns:
            (是否通过, 原因, 高相关证人对列表)
        """
        if len(active_witnesses) < 2:
            return True, "", []
        
        high_correlated_pairs: list[tuple[str, str, float]] = []
        
        # 计算所有证人对的相关性
        for i, w_a in enumerate(active_witnesses):
            for w_b in active_witnesses[i + 1:]:
                # 检查缓存
                cache_key = (min(w_a, w_b), max(w_a, w_b))
                if cache_key in self._correlation_matrix:
                    corr = self._correlation_matrix[cache_key]
                else:
                    corr = self.calculate_correlation(w_a, w_b)
                    self._correlation_matrix[cache_key] = corr
                
                if corr >= self.HIGH_CORRELATION_THRESHOLD:
                    high_correlated_pairs.append((w_a, w_b, corr))
        
        # 检查高相关证人数量
        correlated_witnesses = set()
        for w_a, w_b, _ in high_correlated_pairs:
            correlated_witnesses.add(w_a)
            correlated_witnesses.add(w_b)
        
        if len(correlated_witnesses) > self.MAX_CORRELATED_WITNESSES:
            reason = (
                f"高相关证人过多: {len(correlated_witnesses)} > {self.MAX_CORRELATED_WITNESSES}, "
                f"相关对: {[(a, b, f'{c:.2%}') for a, b, c in high_correlated_pairs]}"
            )
            logger.warning(reason)
            return False, reason, high_correlated_pairs
        
        return True, "", high_correlated_pairs
    
    def get_correlation_matrix(self) -> dict[tuple[str, str], float]:
        """获取相关性矩阵"""
        return self._correlation_matrix.copy()
    
    def clear_history(self) -> None:
        """清除历史数据"""
        self._signal_history.clear()
        self._correlation_matrix.clear()


class RiskControlEngine:
    """
    风控引擎
    
    聚合所有风险域检查器，执行统一的风控检查。
    风控拥有硬否决权，任何检查器拒绝即拒绝。
    """
    
    def __init__(self):
        self._checkers: list[RiskChecker] = []
        self._current_level = RiskLevel.NORMAL
        self._lock_reason: str | None = None
        self._lock_time: datetime | None = None
        self._all_events: list[RiskEvent] = []
        
        # 证人相关性计算器
        self._correlation_calculator = WitnessCorrelationCalculator()
        
        # 初始化默认检查器
        self._init_default_checkers()
    
    def _init_default_checkers(self) -> None:
        """初始化默认风险检查器"""
        self._checkers = [
            AccountRiskChecker(),
            ExecutionRiskChecker(),
            RegimeRiskChecker(),
            BehaviorRiskChecker(),
            SystemRiskChecker(),
        ]
    
    def add_checker(self, checker: RiskChecker) -> None:
        """添加风险检查器"""
        self._checkers.append(checker)
        logger.info(f"添加风险检查器: {checker.name}")
    
    def remove_checker(self, name: str) -> bool:
        """移除风险检查器"""
        for i, checker in enumerate(self._checkers):
            if checker.name == name:
                self._checkers.pop(i)
                logger.info(f"移除风险检查器: {name}")
                return True
        return False
    
    @property
    def current_level(self) -> RiskLevel:
        """当前风控级别"""
        return self._current_level
    
    @property
    def is_locked(self) -> bool:
        """是否被锁定"""
        return self._current_level == RiskLevel.RISK_LOCKED
    
    @property
    def is_cooldown(self) -> bool:
        """是否在冷却期"""
        return self._current_level == RiskLevel.COOLDOWN
    
    async def check_permission(self, context: RiskContext) -> RiskCheckResult:
        """
        检查是否允许交易
        
        Args:
            context: 风控上下文
        
        Returns:
            风控检查结果
        """
        # 如果已锁定，直接拒绝
        if self.is_locked:
            return RiskCheckResult(
                approved=False,
                level=RiskLevel.RISK_LOCKED,
                reason=f"系统已锁定: {self._lock_reason}",
            )
        
        all_events: list[RiskEvent] = []
        highest_level = RiskLevel.NORMAL
        
        # 执行所有检查器
        for checker in self._checkers:
            try:
                result = await checker.check(context)
                all_events.extend(result.events)
                
                # 更新最高风险级别
                if self._level_priority(result.level) > self._level_priority(highest_level):
                    highest_level = result.level
                
                # 任何检查器拒绝即拒绝（硬否决权）
                if not result.approved:
                    logger.warning(
                        f"风控拒绝 [{checker.name}]: {result.reason}",
                        extra={"level": result.level.value},
                    )
                    
                    # 更新状态
                    self._current_level = result.level
                    if result.level == RiskLevel.RISK_LOCKED:
                        self._lock_reason = result.reason
                        self._lock_time = utc_now()
                    
                    return RiskCheckResult(
                        approved=False,
                        level=result.level,
                        reason=result.reason,
                        events=all_events,
                    )
                    
            except Exception as e:
                logger.error(f"风控检查器异常 [{checker.name}]: {e}")
                # 检查器异常时保守处理，拒绝交易
                return RiskCheckResult(
                    approved=False,
                    level=RiskLevel.WARNING,
                    reason=f"风控检查异常: {checker.name}",
                )
        
        # 更新状态
        self._current_level = highest_level
        self._all_events.extend(all_events)
        
        return RiskCheckResult(
            approved=True,
            level=highest_level,
            events=all_events,
        )
    
    async def force_lock(self, reason: str) -> None:
        """
        强制锁定系统
        
        Args:
            reason: 锁定原因
        """
        self._current_level = RiskLevel.RISK_LOCKED
        self._lock_reason = reason
        self._lock_time = utc_now()
        logger.warning(f"系统强制锁定: {reason}")
    
    async def force_cooldown(self, reason: str) -> None:
        """
        强制进入冷却期
        
        Args:
            reason: 冷却原因
        """
        if not self.is_locked:
            self._current_level = RiskLevel.COOLDOWN
            logger.warning(f"系统进入冷却期: {reason}")
    
    async def request_unlock(self) -> bool:
        """
        请求解锁
        
        Returns:
            是否解锁成功
        """
        # 解锁需要外部验证，这里只是接口
        # 实际解锁逻辑在 RecoveryManager 中
        return False
    
    def reset_to_normal(self) -> None:
        """重置为正常状态（仅供恢复管理器调用）"""
        self._current_level = RiskLevel.NORMAL
        self._lock_reason = None
        self._lock_time = None
        logger.info("风控状态重置为 NORMAL")
    
    def _level_priority(self, level: RiskLevel) -> int:
        """获取风险级别优先级"""
        priorities = {
            RiskLevel.NORMAL: 0,
            RiskLevel.WARNING: 1,
            RiskLevel.COOLDOWN: 2,
            RiskLevel.RISK_LOCKED: 3,
        }
        return priorities.get(level, 0)
    
    # ========================================
    # 证人相关性检查
    # ========================================
    
    def record_witness_signal(
        self,
        witness_id: str,
        timestamp: datetime,
        direction: str,
        result: bool,
    ) -> None:
        """
        记录证人信号结果（用于相关性计算）
        
        Args:
            witness_id: 证人 ID
            timestamp: 信号时间
            direction: 信号方向 (long/short)
            result: 交易结果 (True=盈利, False=亏损)
        """
        self._correlation_calculator.record_signal(
            witness_id, timestamp, direction, result
        )
    
    async def check_witness_correlation(
        self,
        active_witnesses: list[str],
    ) -> RiskCheckResult:
        """
        检查证人相关性风险
        
        Args:
            active_witnesses: 当前激活的证人 ID 列表
        
        Returns:
            风控检查结果
        """
        passed, reason, pairs = self._correlation_calculator.check_correlation_risk(
            active_witnesses
        )
        
        if not passed:
            return RiskCheckResult(
                approved=False,
                level=RiskLevel.WARNING,
                reason=reason,
            )
        
        return RiskCheckResult(
            approved=True,
            level=RiskLevel.NORMAL,
        )
    
    def get_witness_correlation(self, witness_a: str, witness_b: str) -> float:
        """获取两个证人之间的相关性"""
        return self._correlation_calculator.calculate_correlation(witness_a, witness_b)
    
    def get_correlation_matrix(self) -> dict[tuple[str, str], float]:
        """获取完整的相关性矩阵"""
        return self._correlation_calculator.get_correlation_matrix()
