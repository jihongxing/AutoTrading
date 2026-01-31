"""
BTC 自动交易系统 — 资金费率异常检测器

检测资金费率极端值事件。
"""

import statistics
import uuid
from datetime import datetime

from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import FundingRate
from src.common.utils import utc_now

from ...pool.models import AnomalyEvent, Hypothesis
from .base import BaseDetector

logger = get_logger(__name__)


class FundingDetector(BaseDetector):
    """
    资金费率异常检测器
    
    检测：
    - 极端正费率（> P95）→ 做空信号
    - 极端负费率（< P5）→ 做多信号
    """
    
    detector_id = "funding"
    detector_name = "资金费率检测器"
    
    def __init__(
        self,
        high_percentile: float = 0.95,
        low_percentile: float = 0.05,
        history_period: int = 100,
    ):
        self.high_percentile = high_percentile
        self.low_percentile = low_percentile
        self.history_period = history_period

    async def detect(self, data: list) -> list[AnomalyEvent]:
        """检测资金费率异常（接收 FundingRate 列表）"""
        if len(data) < self.history_period + 1:
            return []
        
        events = []
        
        # 提取费率
        rates = [item.funding_rate if hasattr(item, 'funding_rate') else item for item in data]
        history_rates = rates[-self.history_period - 1:-1]
        current_rate = rates[-1]
        
        # 计算百分位
        sorted_rates = sorted(history_rates)
        high_idx = int(len(sorted_rates) * self.high_percentile)
        low_idx = int(len(sorted_rates) * self.low_percentile)
        
        high_threshold = sorted_rates[min(high_idx, len(sorted_rates) - 1)]
        low_threshold = sorted_rates[max(low_idx, 0)]
        
        timestamp = utc_now()
        if hasattr(data[-1], 'ts'):
            from src.common.utils import from_utc_ms
            timestamp = from_utc_ms(data[-1].ts)
        
        # 检测极端正费率
        if current_rate > high_threshold:
            severity = min((current_rate - high_threshold) / abs(high_threshold + 0.0001), 1.0)
            events.append(AnomalyEvent(
                event_id=f"funding_high_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="funding_extreme_high",
                timestamp=timestamp,
                severity=abs(severity),
                features={
                    "funding_rate": current_rate,
                    "threshold": high_threshold,
                    "percentile": self.high_percentile,
                },
            ))
            logger.info(f"检测到极端正费率: {current_rate:.4f}")
        
        # 检测极端负费率
        if current_rate < low_threshold:
            severity = min((low_threshold - current_rate) / abs(low_threshold + 0.0001), 1.0)
            events.append(AnomalyEvent(
                event_id=f"funding_low_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="funding_extreme_low",
                timestamp=timestamp,
                severity=abs(severity),
                features={
                    "funding_rate": current_rate,
                    "threshold": low_threshold,
                    "percentile": self.low_percentile,
                },
            ))
            logger.info(f"检测到极端负费率: {current_rate:.4f}")
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从资金费率事件生成假设"""
        hypotheses = []
        
        for event in events:
            if event.event_type == "funding_extreme_high":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="极端正费率做空",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="funding_rate > P95",
                    event_params={"percentile": self.high_percentile},
                    expected_direction="short",
                    expected_win_rate=(0.52, 0.55),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
            
            elif event.event_type == "funding_extreme_low":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="极端负费率做多",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="funding_rate < P5",
                    event_params={"percentile": self.low_percentile},
                    expected_direction="long",
                    expected_win_rate=(0.52, 0.55),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
        
        return hypotheses
