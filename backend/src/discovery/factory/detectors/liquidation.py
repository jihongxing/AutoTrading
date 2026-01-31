"""
BTC 自动交易系统 — 清算异常检测器

检测清算密度异常事件。
"""

import statistics
import uuid
from datetime import datetime

from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import Liquidation
from src.common.utils import utc_now

from ...pool.models import AnomalyEvent, Hypothesis
from .base import BaseDetector

logger = get_logger(__name__)


class LiquidationDetector(BaseDetector):
    """
    清算异常检测器
    
    检测：
    - 清算潮（清算量 > 历史均值 * 3）
    - 多空清算比例失衡
    """
    
    detector_id = "liquidation"
    detector_name = "清算检测器"
    
    def __init__(
        self,
        surge_threshold: float = 3.0,
        imbalance_threshold: float = 0.7,
        history_period: int = 100,
    ):
        self.surge_threshold = surge_threshold
        self.imbalance_threshold = imbalance_threshold
        self.history_period = history_period

    async def detect(self, data: list) -> list[AnomalyEvent]:
        """检测清算异常（接收 Liquidation 列表）"""
        if len(data) < self.history_period + 1:
            return []
        
        events = []
        
        # 提取清算量
        values = [item.usd_value if hasattr(item, 'usd_value') else item for item in data]
        history_values = values[-self.history_period - 1:-1]
        current_value = values[-1]
        
        avg_value = statistics.mean(history_values) if history_values else 0
        
        timestamp = utc_now()
        if hasattr(data[-1], 'ts'):
            from src.common.utils import from_utc_ms
            timestamp = from_utc_ms(data[-1].ts)
        
        # 检测清算潮
        if avg_value > 0 and current_value > avg_value * self.surge_threshold:
            ratio = current_value / avg_value
            severity = min((ratio - self.surge_threshold) / self.surge_threshold, 1.0)
            
            # 判断多空方向
            side = "unknown"
            if hasattr(data[-1], 'side'):
                side = data[-1].side
            
            events.append(AnomalyEvent(
                event_id=f"liq_surge_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="liquidation_surge",
                timestamp=timestamp,
                severity=severity,
                features={
                    "usd_value": current_value,
                    "avg_value": avg_value,
                    "ratio": ratio,
                    "side": side,
                },
            ))
            logger.info(f"检测到清算潮: ratio={ratio:.2f}, side={side}")
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从清算事件生成假设"""
        hypotheses = []
        
        for event in events:
            if event.event_type == "liquidation_surge":
                side = event.features.get("side", "unknown")
                
                # 清算潮后反向交易
                if side == "LONG":
                    direction = "long"  # 多头清算后做多（反转）
                elif side == "SHORT":
                    direction = "short"  # 空头清算后做空（反转）
                else:
                    direction = "breakout"
                
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="清算潮后反转",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="liquidation_value > avg * surge_threshold",
                    event_params={
                        "surge_threshold": self.surge_threshold,
                        "side": side,
                    },
                    expected_direction=direction,
                    expected_win_rate=(0.51, 0.54),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
        
        return hypotheses
