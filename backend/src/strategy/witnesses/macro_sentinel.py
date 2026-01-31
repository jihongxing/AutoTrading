"""
BTC 自动交易系统 — 宏观事件证人（TIER 3）

具有一票否决权的宏观事件证人。
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from src.common.enums import ClaimType, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar
from src.common.utils import utc_now

from ..base import BaseStrategy

logger = get_logger(__name__)


class MacroEventType(str, Enum):
    """宏观事件类型"""
    FED_MEETING = "fed_meeting"
    CPI_RELEASE = "cpi_release"
    NFP_RELEASE = "nfp_release"
    HALVING = "halving"
    REGULATORY = "regulatory"
    BLACK_SWAN = "black_swan"


@dataclass
class MacroEvent:
    """宏观事件"""
    event_type: MacroEventType
    timestamp: datetime
    severity: float  # 0-1
    description: str


class MacroSentinelWitness(BaseStrategy):
    """
    宏观事件证人（TIER 3 否决证人）
    
    具有一票否决权：
    1. 重大新闻/政策监控
    2. 极端事件检测
    3. 预定事件日历
    """
    
    def __init__(
        self,
        strategy_id: str = "macro_sentinel",
        event_buffer_hours: int = 2,
        severity_threshold: float = 0.7,
    ):
        super().__init__(
            strategy_id=strategy_id,
            tier=WitnessTier.TIER_3,
            validity_window=240,
        )
        self.event_buffer_hours = event_buffer_hours
        self.severity_threshold = severity_threshold
        
        # 事件日历
        self._scheduled_events: list[MacroEvent] = []
        # 实时事件
        self._active_events: list[MacroEvent] = []
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        """生成宏观事件否决 Claim"""
        current_time = utc_now()
        
        # 检查预定事件
        upcoming_event = self._check_scheduled_events(current_time)
        if upcoming_event:
            logger.warning(
                f"宏观否决: 预定事件 {upcoming_event.event_type.value}",
                extra={"event_type": upcoming_event.event_type.value},
            )
            return self.create_claim(
                claim_type=ClaimType.EXECUTION_VETO,
                confidence=1.0,
                constraints={
                    "veto_reason": "scheduled_macro_event",
                    "event_type": upcoming_event.event_type.value,
                    "event_time": upcoming_event.timestamp.isoformat(),
                    "severity": upcoming_event.severity,
                },
            )
        
        # 检查实时事件
        active_event = self._check_active_events(current_time)
        if active_event:
            logger.warning(
                f"宏观否决: 实时事件 {active_event.event_type.value}",
                extra={"event_type": active_event.event_type.value},
            )
            return self.create_claim(
                claim_type=ClaimType.EXECUTION_VETO,
                confidence=1.0,
                constraints={
                    "veto_reason": "active_macro_event",
                    "event_type": active_event.event_type.value,
                    "description": active_event.description,
                    "severity": active_event.severity,
                },
            )
        
        return None
    
    def _check_scheduled_events(self, current_time: datetime) -> MacroEvent | None:
        """检查预定事件"""
        buffer = timedelta(hours=self.event_buffer_hours)
        
        # 转换为 naive 比较
        ct = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
        
        for event in self._scheduled_events:
            et = event.timestamp.replace(tzinfo=None) if event.timestamp.tzinfo else event.timestamp
            # 事件前后缓冲时间内
            if abs(et - ct) <= buffer:
                if event.severity >= self.severity_threshold:
                    return event
        
        return None
    
    def _check_active_events(self, current_time: datetime) -> MacroEvent | None:
        """检查实时事件"""
        # 转换为 naive 比较
        ct = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
        
        # 清理过期事件
        self._active_events = [
            e for e in self._active_events
            if ct - (e.timestamp.replace(tzinfo=None) if e.timestamp.tzinfo else e.timestamp) < timedelta(hours=24)
        ]
        
        for event in self._active_events:
            if event.severity >= self.severity_threshold:
                return event
        
        return None
    
    def add_scheduled_event(self, event: MacroEvent) -> None:
        """添加预定事件"""
        self._scheduled_events.append(event)
        logger.info(
            f"添加预定事件: {event.event_type.value} at {event.timestamp}",
            extra={"event_type": event.event_type.value},
        )
    
    def report_event(self, event: MacroEvent) -> None:
        """报告实时事件"""
        self._active_events.append(event)
        logger.warning(
            f"实时事件报告: {event.event_type.value} - {event.description}",
            extra={"event_type": event.event_type.value, "severity": event.severity},
        )
    
    def clear_event(self, event_type: MacroEventType) -> None:
        """清除事件"""
        self._active_events = [
            e for e in self._active_events
            if e.event_type != event_type
        ]
