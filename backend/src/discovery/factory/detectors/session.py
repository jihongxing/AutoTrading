"""
BTC 自动交易系统 — 时段异常检测器

检测时段相关异常。
"""

import uuid

from src.analysis import get_session_info, SessionType
from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import MarketBar
from src.common.utils import from_utc_ms, utc_now

from ...pool.models import AnomalyEvent, Hypothesis
from .base import BaseDetector

logger = get_logger(__name__)


class SessionAnomalyDetector(BaseDetector):
    """
    时段异常检测器
    
    检测：
    - 高波动时段开始
    - 低流动性时段
    - 周末异常波动
    """
    
    detector_id = "session_anomaly"
    detector_name = "时段异常检测器"
    
    def __init__(
        self,
        volatility_multiplier: float = 1.5,
    ):
        self.volatility_multiplier = volatility_multiplier
        self._last_session: SessionType | None = None
    
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """检测时段异常"""
        if not data:
            return []
        
        events = []
        session_info = get_session_info()
        last_bar = data[-1]
        timestamp = from_utc_ms(last_bar.ts)
        
        # 检测时段切换
        if self._last_session != session_info.session:
            if session_info.is_high_volatility:
                events.append(AnomalyEvent(
                    event_id=f"session_{last_bar.ts}_{uuid.uuid4().hex[:8]}",
                    detector_id=self.detector_id,
                    event_type="high_volatility_session_start",
                    timestamp=timestamp,
                    severity=0.6,
                    features={
                        "session": session_info.session.value,
                        "hour": session_info.hour,
                        "volatility_factor": session_info.volatility_factor,
                    },
                ))
                logger.info(
                    f"高波动时段开始: {session_info.session.value}",
                    extra={"session": session_info.session.value},
                )
            
            elif session_info.is_low_liquidity:
                events.append(AnomalyEvent(
                    event_id=f"session_{last_bar.ts}_{uuid.uuid4().hex[:8]}",
                    detector_id=self.detector_id,
                    event_type="low_liquidity_session",
                    timestamp=timestamp,
                    severity=0.4,
                    features={
                        "session": session_info.session.value,
                        "hour": session_info.hour,
                        "liquidity_factor": session_info.liquidity_factor,
                    },
                ))
            
            self._last_session = session_info.session
        
        # 检测周末异常波动
        if session_info.is_weekend and len(data) >= 2:
            price_change = abs(data[-1].close - data[-2].close) / data[-2].close
            if price_change > 0.01:  # 1% 以上波动
                events.append(AnomalyEvent(
                    event_id=f"weekend_{last_bar.ts}_{uuid.uuid4().hex[:8]}",
                    detector_id=self.detector_id,
                    event_type="weekend_volatility",
                    timestamp=timestamp,
                    severity=min(price_change / 0.02, 1.0),
                    features={
                        "price_change_pct": price_change,
                        "is_weekend": True,
                    },
                ))
                logger.info(f"周末异常波动: {price_change:.2%}")
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从时段事件生成假设"""
        hypotheses = []
        
        for event in events:
            if event.event_type == "high_volatility_session_start":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="高波动时段突破",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="high_volatility_session_start",
                    event_params={
                        "session": event.features.get("session"),
                    },
                    expected_direction="breakout",
                    expected_win_rate=(0.51, 0.54),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
            
            elif event.event_type == "weekend_volatility":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="周末波动回归",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="weekend_volatility > 1%",
                    event_params={
                        "price_change_pct": event.features.get("price_change_pct"),
                    },
                    expected_direction="mean_reversion",
                    expected_win_rate=(0.50, 0.53),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
        
        return hypotheses
