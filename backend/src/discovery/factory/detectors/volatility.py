"""
BTC 自动交易系统 — 波动率异常检测器

检测波动率压缩/爆发等异常模式。
"""

import uuid
from datetime import datetime

from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import MarketBar
from src.common.utils import utc_now

from ...pool.models import AnomalyEvent, Hypothesis, ValidationResult
from .base import BaseDetector

logger = get_logger(__name__)


class VolatilityDetector(BaseDetector):
    """波动率异常检测器"""
    
    detector_id = "volatility"
    detector_name = "波动率检测器"
    
    def __init__(
        self,
        compression_threshold: float = 0.3,  # ATR 压缩阈值
        expansion_threshold: float = 2.0,    # ATR 扩张阈值
        lookback: int = 20,
    ):
        self.compression_threshold = compression_threshold
        self.expansion_threshold = expansion_threshold
        self.lookback = lookback
    
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """检测波动率异常"""
        if len(data) < self.lookback + 10:
            return []
        
        events = []
        
        # 计算 ATR 序列
        atrs = self._calculate_atr_series(data)
        if len(atrs) < self.lookback:
            return []
        
        # 计算历史 ATR 均值和标准差
        hist_atrs = atrs[:-1]
        avg_atr = sum(hist_atrs[-self.lookback:]) / self.lookback
        
        if avg_atr == 0:
            return []
        
        current_atr = atrs[-1]
        atr_ratio = current_atr / avg_atr
        
        # 检测压缩
        if atr_ratio < self.compression_threshold:
            events.append(AnomalyEvent(
                event_id=f"vol_compress_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="volatility_compression",
                timestamp=data[-1].timestamp,
                severity=1 - atr_ratio,  # 越压缩越严重
                features={
                    "atr_ratio": atr_ratio,
                    "current_atr": current_atr,
                    "avg_atr": avg_atr,
                    "price": data[-1].close,
                },
            ))
        
        # 检测扩张
        if atr_ratio > self.expansion_threshold:
            events.append(AnomalyEvent(
                event_id=f"vol_expand_{uuid.uuid4().hex[:8]}",
                detector_id=self.detector_id,
                event_type="volatility_expansion",
                timestamp=data[-1].timestamp,
                severity=min(1.0, (atr_ratio - 1) / 3),
                features={
                    "atr_ratio": atr_ratio,
                    "current_atr": current_atr,
                    "avg_atr": avg_atr,
                    "price": data[-1].close,
                },
            ))
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从异常事件生成假设"""
        hypotheses = []
        
        for event in events:
            if event.event_type == "volatility_compression":
                # 波动率压缩后通常会有突破
                hypotheses.append(Hypothesis(
                    id=f"hyp_{uuid.uuid4().hex[:8]}",
                    name=f"波动率压缩突破_{event.timestamp.strftime('%Y%m%d')}",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="atr_ratio < compression_threshold",
                    event_params={
                        "compression_threshold": self.compression_threshold,
                        "lookback": float(self.lookback),
                    },
                    expected_direction="breakout",
                    expected_win_rate=(0.45, 0.55),
                ))
            
            elif event.event_type == "volatility_expansion":
                # 波动率扩张后可能回归
                hypotheses.append(Hypothesis(
                    id=f"hyp_{uuid.uuid4().hex[:8]}",
                    name=f"波动率扩张回归_{event.timestamp.strftime('%Y%m%d')}",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="atr_ratio > expansion_threshold",
                    event_params={
                        "expansion_threshold": self.expansion_threshold,
                        "lookback": float(self.lookback),
                    },
                    expected_direction="mean_reversion",
                    expected_win_rate=(0.40, 0.50),
                ))
        
        return hypotheses
    
    def _calculate_atr_series(self, data: list[MarketBar]) -> list[float]:
        """计算 ATR 序列"""
        atrs = []
        for i in range(1, len(data)):
            high = data[i].high
            low = data[i].low
            prev_close = data[i-1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            atrs.append(tr)
        
        # 平滑 ATR
        if len(atrs) < 14:
            return atrs
        
        smoothed = []
        atr = sum(atrs[:14]) / 14
        smoothed.append(atr)
        
        for i in range(14, len(atrs)):
            atr = (atr * 13 + atrs[i]) / 14
            smoothed.append(atr)
        
        return smoothed
