"""
BTC 自动交易系统 — 价格形态检测器

检测双顶、双底等价格形态。
"""

import uuid

from src.analysis import detect_price_pattern, PatternType
from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import MarketBar
from src.common.utils import from_utc_ms, utc_now

from ...pool.models import AnomalyEvent, Hypothesis
from .base import BaseDetector

logger = get_logger(__name__)


class PricePatternDetector(BaseDetector):
    """
    价格形态检测器
    
    检测：
    - 双顶（double_top）
    - 双底（double_bottom）
    - 更高高点（higher_high）
    - 更低低点（lower_low）
    """
    
    detector_id = "price_pattern"
    detector_name = "价格形态检测器"
    
    def __init__(
        self,
        lookback_period: int = 48,
        tolerance: float = 0.01,
    ):
        self.lookback_period = lookback_period
        self.tolerance = tolerance
    
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """检测价格形态"""
        if len(data) < self.lookback_period:
            return []
        
        events = []
        
        result = detect_price_pattern(
            data,
            lookback=self.lookback_period,
            tolerance=self.tolerance,
        )
        
        if result.pattern == PatternType.NONE:
            return []
        
        last_bar = data[-1]
        timestamp = from_utc_ms(last_bar.ts)
        
        events.append(AnomalyEvent(
            event_id=f"pattern_{last_bar.ts}_{uuid.uuid4().hex[:8]}",
            detector_id=self.detector_id,
            event_type=result.pattern.value,
            timestamp=timestamp,
            severity=result.confidence,
            features={
                "pattern": result.pattern.value,
                "confidence": result.confidence,
                "key_levels": result.key_levels,
            },
        ))
        
        logger.info(
            f"检测到价格形态: {result.pattern.value}",
            extra={"pattern": result.pattern.value, "confidence": result.confidence},
        )
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从形态事件生成假设"""
        hypotheses = []
        
        for event in events:
            pattern = event.event_type
            
            if pattern == PatternType.DOUBLE_TOP.value:
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="双顶反转做空",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="double_top_pattern",
                    event_params={"tolerance": self.tolerance},
                    expected_direction="short",
                    expected_win_rate=(0.52, 0.55),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
            
            elif pattern == PatternType.DOUBLE_BOTTOM.value:
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="双底反转做多",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="double_bottom_pattern",
                    event_params={"tolerance": self.tolerance},
                    expected_direction="long",
                    expected_win_rate=(0.52, 0.55),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
            
            elif pattern == PatternType.HIGHER_HIGH.value:
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="更高高点趋势延续",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="higher_high_pattern",
                    event_params={"tolerance": self.tolerance},
                    expected_direction="long",
                    expected_win_rate=(0.51, 0.54),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
            
            elif pattern == PatternType.LOWER_LOW.value:
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="更低低点趋势延续",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="lower_low_pattern",
                    event_params={"tolerance": self.tolerance},
                    expected_direction="short",
                    expected_win_rate=(0.51, 0.54),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
        
        return hypotheses
