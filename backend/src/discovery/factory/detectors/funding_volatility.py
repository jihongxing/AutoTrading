"""
BTC 自动交易系统 — 资金费率波动检测器

检测资金费率异常波动。
"""

import statistics
import uuid

from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import MarketBar
from src.common.utils import from_utc_ms, utc_now

from ...pool.models import AnomalyEvent, Hypothesis
from .base import BaseDetector

logger = get_logger(__name__)


class FundingVolatilityDetector(BaseDetector):
    """
    资金费率波动检测器
    
    检测：
    - 资金费率波动加剧
    - 资金费率方向反转
    
    注：需要 MarketBar 包含 funding_rate 字段，或从外部数据源获取
    """
    
    detector_id = "funding_volatility"
    detector_name = "资金费率波动检测器"
    
    def __init__(
        self,
        volatility_threshold: float = 2.0,
        reversal_threshold: float = 0.0005,
        lookback_period: int = 24,
    ):
        self.volatility_threshold = volatility_threshold
        self.reversal_threshold = reversal_threshold
        self.lookback_period = lookback_period
        self._funding_rates: list[float] = []
    
    def update_funding_rate(self, rate: float) -> None:
        """更新资金费率数据"""
        self._funding_rates.append(rate)
        # 保留最近数据
        if len(self._funding_rates) > self.lookback_period * 2:
            self._funding_rates = self._funding_rates[-self.lookback_period * 2:]
    
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """检测资金费率波动"""
        if len(self._funding_rates) < self.lookback_period:
            return []
        
        if not data:
            return []
        
        events = []
        last_bar = data[-1]
        timestamp = from_utc_ms(last_bar.ts)
        
        recent_rates = self._funding_rates[-self.lookback_period:]
        current_rate = recent_rates[-1]
        
        # 计算波动率
        rate_std = statistics.stdev(recent_rates) if len(recent_rates) > 1 else 0
        rate_mean = statistics.mean(recent_rates)
        
        if rate_std == 0:
            return []
        
        # 检测波动加剧
        recent_changes = [
            abs(recent_rates[i] - recent_rates[i - 1])
            for i in range(1, len(recent_rates))
        ]
        avg_change = statistics.mean(recent_changes) if recent_changes else 0
        
        if len(recent_changes) >= 2:
            historical_change = statistics.mean(recent_changes[:-3]) if len(recent_changes) > 3 else avg_change
            if historical_change > 0:
                volatility_ratio = recent_changes[-1] / historical_change
                
                if volatility_ratio > self.volatility_threshold:
                    events.append(AnomalyEvent(
                        event_id=f"funding_vol_{last_bar.ts}_{uuid.uuid4().hex[:8]}",
                        detector_id=self.detector_id,
                        event_type="funding_volatility_surge",
                        timestamp=timestamp,
                        severity=min(volatility_ratio / (self.volatility_threshold * 2), 1.0),
                        features={
                            "current_rate": current_rate,
                            "volatility_ratio": volatility_ratio,
                            "rate_std": rate_std,
                        },
                    ))
                    logger.info(f"资金费率波动加剧: ratio={volatility_ratio:.2f}")
        
        # 检测方向反转
        if len(recent_rates) >= 3:
            prev_rate = recent_rates[-2]
            prev_prev_rate = recent_rates[-3]
            
            # 从正转负
            if prev_prev_rate > 0 and prev_rate > 0 and current_rate < -self.reversal_threshold:
                events.append(AnomalyEvent(
                    event_id=f"funding_rev_{last_bar.ts}_{uuid.uuid4().hex[:8]}",
                    detector_id=self.detector_id,
                    event_type="funding_reversal_negative",
                    timestamp=timestamp,
                    severity=min(abs(current_rate) / 0.001, 1.0),
                    features={
                        "current_rate": current_rate,
                        "prev_rate": prev_rate,
                        "direction": "negative",
                    },
                ))
                logger.info(f"资金费率转负: {current_rate:.6f}")
            
            # 从负转正
            elif prev_prev_rate < 0 and prev_rate < 0 and current_rate > self.reversal_threshold:
                events.append(AnomalyEvent(
                    event_id=f"funding_rev_{last_bar.ts}_{uuid.uuid4().hex[:8]}",
                    detector_id=self.detector_id,
                    event_type="funding_reversal_positive",
                    timestamp=timestamp,
                    severity=min(abs(current_rate) / 0.001, 1.0),
                    features={
                        "current_rate": current_rate,
                        "prev_rate": prev_rate,
                        "direction": "positive",
                    },
                ))
                logger.info(f"资金费率转正: {current_rate:.6f}")
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从资金费率事件生成假设"""
        hypotheses = []
        
        for event in events:
            if event.event_type == "funding_volatility_surge":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="资金费率波动后价格跟随",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="funding_volatility > threshold",
                    event_params={
                        "volatility_threshold": self.volatility_threshold,
                    },
                    expected_direction="trend",
                    expected_win_rate=(0.51, 0.54),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
            
            elif event.event_type == "funding_reversal_negative":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="资金费率转负做空",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="funding_rate reversal to negative",
                    event_params={
                        "reversal_threshold": self.reversal_threshold,
                    },
                    expected_direction="short",
                    expected_win_rate=(0.52, 0.55),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
            
            elif event.event_type == "funding_reversal_positive":
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="资金费率转正做多",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="funding_rate reversal to positive",
                    event_params={
                        "reversal_threshold": self.reversal_threshold,
                    },
                    expected_direction="long",
                    expected_win_rate=(0.52, 0.55),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
        
        return hypotheses
