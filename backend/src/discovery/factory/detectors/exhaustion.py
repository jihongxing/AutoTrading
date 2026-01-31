"""
BTC 自动交易系统 — 趋势耗竭检测器

检测趋势耗竭信号（RSI 背离）。
"""

import uuid

from src.analysis import detect_trend_exhaustion
from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import MarketBar
from src.common.utils import from_utc_ms, utc_now

from ...pool.models import AnomalyEvent, Hypothesis
from .base import BaseDetector

logger = get_logger(__name__)


class TrendExhaustionDetector(BaseDetector):
    """
    趋势耗竭检测器
    
    检测：
    - 上涨耗竭（价格新高但 RSI 未新高）
    - 下跌耗竭（价格新低但 RSI 未新低）
    """
    
    detector_id = "trend_exhaustion"
    detector_name = "趋势耗竭检测器"
    
    def __init__(
        self,
        rsi_period: int = 14,
        lookback: int = 5,
        divergence_threshold: float = 0.02,
    ):
        self.rsi_period = rsi_period
        self.lookback = lookback
        self.divergence_threshold = divergence_threshold
    
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """检测趋势耗竭"""
        if len(data) < self.rsi_period + self.lookback + 1:
            return []
        
        events = []
        
        result = detect_trend_exhaustion(
            data,
            rsi_period=self.rsi_period,
            lookback=self.lookback,
            divergence_threshold=self.divergence_threshold,
        )
        
        if not result.is_exhausted:
            return []
        
        last_bar = data[-1]
        timestamp = from_utc_ms(last_bar.ts)
        
        event_type = f"exhaustion_{result.direction}"
        
        events.append(AnomalyEvent(
            event_id=f"exhaust_{last_bar.ts}_{uuid.uuid4().hex[:8]}",
            detector_id=self.detector_id,
            event_type=event_type,
            timestamp=timestamp,
            severity=result.strength,
            features={
                "direction": result.direction,
                "strength": result.strength,
                "divergence": result.divergence,
            },
        ))
        
        logger.info(
            f"检测到趋势耗竭: direction={result.direction}, strength={result.strength:.2f}",
            extra={"event_type": event_type, "strength": result.strength},
        )
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从耗竭事件生成假设"""
        hypotheses = []
        
        for event in events:
            direction = event.features.get("direction", "up")
            
            # 耗竭后反转
            hypotheses.append(Hypothesis(
                id=f"hyp_{event.event_id}",
                name=f"{'上涨' if direction == 'up' else '下跌'}耗竭反转",
                status=HypothesisStatus.NEW,
                source_detector=self.detector_id,
                source_event=event.event_id,
                event_definition=f"exhaustion_{direction}_divergence",
                event_params={
                    "rsi_period": self.rsi_period,
                    "divergence_threshold": self.divergence_threshold,
                },
                expected_direction="short" if direction == "up" else "long",
                expected_win_rate=(0.52, 0.55),
                created_at=utc_now(),
                updated_at=utc_now(),
            ))
        
        return hypotheses
