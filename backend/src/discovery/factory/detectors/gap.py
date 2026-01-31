"""
BTC 自动交易系统 — 跳空检测器

检测价格跳空事件。
"""

import uuid

from src.analysis import detect_gap
from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import MarketBar
from src.common.utils import from_utc_ms, utc_now

from ...pool.models import AnomalyEvent, Hypothesis
from .base import BaseDetector

logger = get_logger(__name__)


class GapDetector(BaseDetector):
    """
    跳空检测器
    
    检测：
    - 向上跳空（gap > threshold）
    - 向下跳空（gap < -threshold）
    """
    
    detector_id = "gap"
    detector_name = "跳空检测器"
    
    def __init__(
        self,
        gap_threshold: float = 0.005,
        large_gap_threshold: float = 0.01,
    ):
        self.gap_threshold = gap_threshold
        self.large_gap_threshold = large_gap_threshold
    
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """检测跳空"""
        if len(data) < 2:
            return []
        
        events = []
        prev_bar = data[-2]
        current_bar = data[-1]
        
        # 使用 analysis 模块检测跳空
        result = detect_gap(prev_bar, current_bar, threshold=self.gap_threshold)
        
        if not result.has_gap:
            return []
        
        timestamp = from_utc_ms(current_bar.ts)
        is_large = result.gap_pct >= self.large_gap_threshold
        
        event_type = f"gap_{result.direction}"
        if is_large:
            event_type = f"large_{event_type}"
        
        severity = min(result.gap_pct / self.large_gap_threshold, 1.0)
        
        events.append(AnomalyEvent(
            event_id=f"gap_{current_bar.ts}_{uuid.uuid4().hex[:8]}",
            detector_id=self.detector_id,
            event_type=event_type,
            timestamp=timestamp,
            severity=severity,
            features={
                "direction": result.direction,
                "gap_size": result.gap_size,
                "gap_pct": result.gap_pct,
                "is_large": is_large,
            },
        ))
        
        logger.info(
            f"检测到跳空: direction={result.direction}, gap_pct={result.gap_pct:.4f}",
            extra={"event_type": event_type, "gap_pct": result.gap_pct},
        )
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从跳空事件生成假设"""
        hypotheses = []
        
        for event in events:
            direction = event.features.get("direction", "up")
            is_large = event.features.get("is_large", False)
            
            # 假设：跳空回补
            hypotheses.append(Hypothesis(
                id=f"hyp_{event.event_id}_fill",
                name="跳空回补",
                status=HypothesisStatus.NEW,
                source_detector=self.detector_id,
                source_event=event.event_id,
                event_definition=f"gap_{direction} > threshold",
                event_params={
                    "gap_threshold": self.gap_threshold,
                    "direction": direction,
                },
                expected_direction="short" if direction == "up" else "long",
                expected_win_rate=(0.52, 0.55) if is_large else (0.50, 0.53),
                created_at=utc_now(),
                updated_at=utc_now(),
            ))
            
            # 假设：跳空延续（大跳空）
            if is_large:
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}_continue",
                    name="跳空延续",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition=f"large_gap_{direction}",
                    event_params={
                        "large_gap_threshold": self.large_gap_threshold,
                        "direction": direction,
                    },
                    expected_direction="long" if direction == "up" else "short",
                    expected_win_rate=(0.51, 0.54),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
        
        return hypotheses
