"""
BTC 自动交易系统 — 成交量异常检测器

检测成交量激增/萎缩等异常模式。
"""

import uuid

from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import MarketBar
from src.common.utils import utc_now

from ...pool.models import AnomalyEvent, Hypothesis
from .base import BaseDetector

logger = get_logger(__name__)


class VolumeDetector(BaseDetector):
    """成交量异常检测器"""
    
    detector_id = "volume"
    detector_name = "成交量检测器"
    
    def __init__(
        self,
        surge_threshold: float = 3.0,   # 成交量激增阈值（倍数）
        dry_threshold: float = 0.3,     # 成交量萎缩阈值
        lookback: int = 20,
    ):
        self.surge_threshold = surge_threshold
        self.dry_threshold = dry_threshold
        self.lookback = lookback
    
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """检测成交量异常"""
        if len(data) < self.lookback + 5:
            return []
        
        events = []
        
        # 计算历史成交量均值
        volumes = [bar.volume for bar in data]
        hist_volumes = volumes[-(self.lookback + 1):-1]
        avg_volume = sum(hist_volumes) / len(hist_volumes)
        
        if avg_volume == 0:
            return []
        
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume
        
        # 检测激增
        if volume_ratio > self.surge_threshold:
            # 判断方向
            price_change = (data[-1].close - data[-2].close) / data[-2].close
            direction = "bullish" if price_change > 0 else "bearish"
            
            events.append(AnomalyEvent(
                event_id=f"vol_surge_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="volume_surge",
                timestamp=data[-1].timestamp,
                severity=min(1.0, (volume_ratio - 1) / 5),
                features={
                    "volume_ratio": volume_ratio,
                    "current_volume": current_volume,
                    "avg_volume": avg_volume,
                    "price_change": price_change,
                    "direction": 1.0 if direction == "bullish" else -1.0,
                },
            ))
        
        # 检测萎缩
        if volume_ratio < self.dry_threshold:
            events.append(AnomalyEvent(
                event_id=f"vol_dry_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="volume_dry",
                timestamp=data[-1].timestamp,
                severity=1 - volume_ratio,
                features={
                    "volume_ratio": volume_ratio,
                    "current_volume": current_volume,
                    "avg_volume": avg_volume,
                },
            ))
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从异常事件生成假设"""
        hypotheses = []
        
        for event in events:
            if event.event_type == "volume_surge":
                direction = "long" if event.features.get("direction", 0) > 0 else "short"
                hypotheses.append(Hypothesis(
                    id=f"hyp_{uuid.uuid4().hex[:8]}",
                    name=f"放量{direction}_{event.timestamp.strftime('%Y%m%d')}",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="volume_ratio > surge_threshold AND direction == expected",
                    event_params={
                        "surge_threshold": self.surge_threshold,
                        "lookback": float(self.lookback),
                    },
                    expected_direction=direction,
                    expected_win_rate=(0.48, 0.58),
                ))
            
            elif event.event_type == "volume_dry":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{uuid.uuid4().hex[:8]}",
                    name=f"缩量观望_{event.timestamp.strftime('%Y%m%d')}",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="volume_ratio < dry_threshold",
                    event_params={
                        "dry_threshold": self.dry_threshold,
                        "lookback": float(self.lookback),
                    },
                    expected_direction="neutral",
                    expected_win_rate=(0.40, 0.50),
                ))
        
        return hypotheses
