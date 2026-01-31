"""
BTC 自动交易系统 — 行为风控

监控交易频率、持仓集中度、方向性集中度。
"""

from src.common.enums import RiskEventType, RiskLevel
from src.common.logging import get_logger
from src.common.models import RiskCheckResult, RiskEvent

from .base import RiskChecker, RiskContext
from .constants import RiskThresholds

logger = get_logger(__name__)


class BehaviorRiskChecker(RiskChecker):
    """
    系统行为风控检查器
    
    检查项：
    - 交易频率
    - 持仓集中度
    - 方向性集中度
    """
    
    @property
    def name(self) -> str:
        return "behavior_risk"
    
    def __init__(
        self,
        max_trades_per_hour: int = 10,
        max_single_position: float | None = None,
        max_total_position: float | None = None,
        max_direction_ratio: float = 0.80,
    ):
        self.max_trades_per_hour = max_trades_per_hour
        self.max_single_position = max_single_position or RiskThresholds.position.max_single_position
        self.max_total_position = max_total_position or RiskThresholds.position.max_total_position
        self.max_direction_ratio = max_direction_ratio
    
    async def check(self, context: RiskContext) -> RiskCheckResult:
        """执行行为风控检查"""
        events: list[RiskEvent] = []
        
        # 检查交易频率
        if len(context.recent_trades) > self.max_trades_per_hour:
            event = self._create_event(
                event_type=RiskEventType.EXECUTION_FAILURE.value,
                level=RiskLevel.WARNING,
                description=f"交易频率 {len(context.recent_trades)}/h 超过阈值 {self.max_trades_per_hour}/h",
                value=float(len(context.recent_trades)),
                threshold=float(self.max_trades_per_hour),
            )
            events.append(event)
            logger.warning(f"交易频率过高: {len(context.recent_trades)}/h")
        
        # 检查单笔仓位
        if context.requested_position > self.max_single_position:
            event = self._create_event(
                event_type=RiskEventType.EXECUTION_FAILURE.value,
                level=RiskLevel.WARNING,
                description=f"请求仓位 {context.requested_position:.2%} 超过单笔上限 {self.max_single_position:.2%}",
                value=context.requested_position,
                threshold=self.max_single_position,
            )
            events.append(event)
            logger.warning(f"单笔仓位过大: {context.requested_position:.2%}")
            return self._reject(
                level=RiskLevel.WARNING,
                reason="单笔仓位超过上限",
                events=events,
            )
        
        # 检查总仓位
        total_position = context.current_position + context.requested_position
        if total_position > self.max_total_position:
            event = self._create_event(
                event_type=RiskEventType.EXECUTION_FAILURE.value,
                level=RiskLevel.WARNING,
                description=f"总仓位 {total_position:.2%} 超过上限 {self.max_total_position:.2%}",
                value=total_position,
                threshold=self.max_total_position,
            )
            events.append(event)
            logger.warning(f"总仓位过大: {total_position:.2%}")
            return self._reject(
                level=RiskLevel.WARNING,
                reason="总仓位超过上限",
                events=events,
            )
        
        # 检查方向集中度
        if context.recent_trades:
            long_count = sum(1 for t in context.recent_trades if t.direction == "long")
            short_count = len(context.recent_trades) - long_count
            total = len(context.recent_trades)
            
            if total > 0:
                direction_ratio = max(long_count, short_count) / total
                if direction_ratio > self.max_direction_ratio:
                    dominant = "long" if long_count > short_count else "short"
                    event = self._create_event(
                        event_type=RiskEventType.EXECUTION_FAILURE.value,
                        level=RiskLevel.WARNING,
                        description=f"方向集中度 {direction_ratio:.2%} ({dominant}) 过高",
                        value=direction_ratio,
                        threshold=self.max_direction_ratio,
                    )
                    events.append(event)
                    logger.warning(f"方向集中度过高: {direction_ratio:.2%} ({dominant})")
        
        if events:
            return RiskCheckResult(
                approved=True,
                level=RiskLevel.WARNING,
                events=events,
            )
        
        return self._approve()
