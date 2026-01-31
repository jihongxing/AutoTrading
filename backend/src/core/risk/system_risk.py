"""
BTC 自动交易系统 — 系统稳定性风控

监控模块通信延迟、数据完整性、状态同步。
"""

from datetime import timedelta

from src.common.enums import RiskEventType, RiskLevel
from src.common.logging import get_logger
from src.common.models import RiskCheckResult, RiskEvent
from src.common.utils import utc_now

from .base import RiskChecker, RiskContext

logger = get_logger(__name__)


class SystemRiskChecker(RiskChecker):
    """
    系统稳定性风控检查器
    
    检查项：
    - 模块通信延迟
    - 数据完整性
    - 状态同步
    """
    
    @property
    def name(self) -> str:
        return "system_risk"
    
    def __init__(
        self,
        max_data_delay_ms: int = 5000,
        max_heartbeat_gap_seconds: int = 30,
    ):
        self.max_data_delay_ms = max_data_delay_ms
        self.max_heartbeat_gap_seconds = max_heartbeat_gap_seconds
    
    async def check(self, context: RiskContext) -> RiskCheckResult:
        """执行系统稳定性风控检查"""
        events: list[RiskEvent] = []
        
        # 检查数据延迟
        if context.data_delay_ms > self.max_data_delay_ms:
            event = self._create_event(
                event_type=RiskEventType.EXECUTION_FAILURE.value,
                level=RiskLevel.WARNING,
                description=f"数据延迟 {context.data_delay_ms}ms 超过阈值 {self.max_data_delay_ms}ms",
                value=float(context.data_delay_ms),
                threshold=float(self.max_data_delay_ms),
            )
            events.append(event)
            logger.warning(f"数据延迟过高: {context.data_delay_ms}ms")
            
            # 延迟严重时拒绝交易
            if context.data_delay_ms > self.max_data_delay_ms * 2:
                return self._reject(
                    level=RiskLevel.COOLDOWN,
                    reason="数据延迟严重",
                    events=events,
                )
        
        # 检查心跳
        if context.last_heartbeat:
            gap = utc_now() - context.last_heartbeat
            if gap > timedelta(seconds=self.max_heartbeat_gap_seconds):
                event = self._create_event(
                    event_type=RiskEventType.EXECUTION_FAILURE.value,
                    level=RiskLevel.WARNING,
                    description=f"心跳间隔 {gap.total_seconds():.0f}s 超过阈值 {self.max_heartbeat_gap_seconds}s",
                    value=gap.total_seconds(),
                    threshold=float(self.max_heartbeat_gap_seconds),
                )
                events.append(event)
                logger.warning(f"心跳间隔过长: {gap.total_seconds():.0f}s")
                
                # 心跳丢失严重时拒绝
                if gap > timedelta(seconds=self.max_heartbeat_gap_seconds * 3):
                    return self._reject(
                        level=RiskLevel.COOLDOWN,
                        reason="系统心跳丢失",
                        events=events,
                    )
        
        if events:
            return RiskCheckResult(
                approved=True,
                level=RiskLevel.WARNING,
                events=events,
            )
        
        return self._approve()
