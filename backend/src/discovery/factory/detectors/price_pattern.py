"""
BTC 自动交易系统 — 价格形态检测器

检测关键价格形态（突破、假突破、支撑阻力等）。
"""

import uuid

from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import MarketBar

from ...pool.models import AnomalyEvent, Hypothesis
from .base import BaseDetector

logger = get_logger(__name__)


class PricePatternDetector(BaseDetector):
    """价格形态检测器"""
    
    detector_id = "price_pattern"
    detector_name = "价格形态检测器"
    
    def __init__(
        self,
        breakout_threshold: float = 0.02,  # 突破阈值 2%
        false_breakout_bars: int = 3,      # 假突破判定K线数
        lookback: int = 20,
    ):
        self.breakout_threshold = breakout_threshold
        self.false_breakout_bars = false_breakout_bars
        self.lookback = lookback
    
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """检测价格形态异常"""
        if len(data) < self.lookback + 10:
            return []
        
        events = []
        
        # 计算近期高低点
        recent = data[-(self.lookback + 1):-1]
        high_level = max(bar.high for bar in recent)
        low_level = min(bar.low for bar in recent)
        
        current = data[-1]
        prev = data[-2]
        
        # 检测向上突破
        if current.close > high_level * (1 + self.breakout_threshold):
            events.append(AnomalyEvent(
                event_id=f"breakout_up_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="breakout_up",
                timestamp=current.timestamp,
                severity=min(1.0, (current.close / high_level - 1) / 0.05),
                features={
                    "high_level": high_level,
                    "low_level": low_level,
                    "close": current.close,
                    "breakout_pct": (current.close - high_level) / high_level,
                },
            ))
        
        # 检测向下突破
        if current.close < low_level * (1 - self.breakout_threshold):
            events.append(AnomalyEvent(
                event_id=f"breakout_down_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="breakout_down",
                timestamp=current.timestamp,
                severity=min(1.0, (1 - current.close / low_level) / 0.05),
                features={
                    "high_level": high_level,
                    "low_level": low_level,
                    "close": current.close,
                    "breakout_pct": (low_level - current.close) / low_level,
                },
            ))
        
        # 检测假突破（先突破后回落）
        if len(data) >= self.false_breakout_bars + self.lookback:
            fb_events = self._detect_false_breakout(data, high_level, low_level)
            events.extend(fb_events)
        
        return events
    
    def _detect_false_breakout(
        self,
        data: list[MarketBar],
        high_level: float,
        low_level: float,
    ) -> list[AnomalyEvent]:
        """检测假突破"""
        events = []
        
        # 检查最近几根K线是否有假突破
        recent_bars = data[-self.false_breakout_bars:]
        
        # 向上假突破：曾突破高点但收回
        max_high = max(bar.high for bar in recent_bars)
        current_close = data[-1].close
        
        if max_high > high_level and current_close < high_level:
            events.append(AnomalyEvent(
                event_id=f"false_breakout_up_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="false_breakout_up",
                timestamp=data[-1].timestamp,
                severity=0.7,
                features={
                    "high_level": high_level,
                    "max_high": max_high,
                    "current_close": current_close,
                },
            ))
        
        # 向下假突破
        min_low = min(bar.low for bar in recent_bars)
        
        if min_low < low_level and current_close > low_level:
            events.append(AnomalyEvent(
                event_id=f"false_breakout_down_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="false_breakout_down",
                timestamp=data[-1].timestamp,
                severity=0.7,
                features={
                    "low_level": low_level,
                    "min_low": min_low,
                    "current_close": current_close,
                },
            ))
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从异常事件生成假设"""
        hypotheses = []
        
        for event in events:
            if event.event_type == "breakout_up":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{uuid.uuid4().hex[:8]}",
                    name=f"向上突破追多_{event.timestamp.strftime('%Y%m%d')}",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="close > high_level * (1 + threshold)",
                    event_params={
                        "threshold": self.breakout_threshold,
                        "lookback": float(self.lookback),
                    },
                    expected_direction="long",
                    expected_win_rate=(0.45, 0.55),
                ))
            
            elif event.event_type == "breakout_down":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{uuid.uuid4().hex[:8]}",
                    name=f"向下突破追空_{event.timestamp.strftime('%Y%m%d')}",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="close < low_level * (1 - threshold)",
                    event_params={
                        "threshold": self.breakout_threshold,
                        "lookback": float(self.lookback),
                    },
                    expected_direction="short",
                    expected_win_rate=(0.45, 0.55),
                ))
            
            elif event.event_type == "false_breakout_up":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{uuid.uuid4().hex[:8]}",
                    name=f"假突破做空_{event.timestamp.strftime('%Y%m%d')}",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="high > high_level AND close < high_level",
                    event_params={
                        "lookback": float(self.lookback),
                        "false_breakout_bars": float(self.false_breakout_bars),
                    },
                    expected_direction="short",
                    expected_win_rate=(0.50, 0.60),
                ))
            
            elif event.event_type == "false_breakout_down":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{uuid.uuid4().hex[:8]}",
                    name=f"假突破做多_{event.timestamp.strftime('%Y%m%d')}",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="low < low_level AND close > low_level",
                    event_params={
                        "lookback": float(self.lookback),
                        "false_breakout_bars": float(self.false_breakout_bars),
                    },
                    expected_direction="long",
                    expected_win_rate=(0.50, 0.60),
                ))
        
        return hypotheses
