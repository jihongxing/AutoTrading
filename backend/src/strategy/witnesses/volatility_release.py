"""
BTC 自动交易系统 — 波动率释放证人（TIER 1）

检测波动率压缩后的释放信号。
"""

from datetime import datetime

from src.analysis import calculate_atr, detect_compression
from src.common.enums import ClaimType, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar
from src.common.utils import utc_now

from ..base import BaseStrategy

logger = get_logger(__name__)


class VolatilityReleaseWitness(BaseStrategy):
    """
    波动率释放证人（TIER 1 核心证人）
    
    检测波动率压缩后的释放信号：
    1. 波动率压缩检测（ATR 收缩）
    2. 突破确认
    3. 时间衰减因子
    """
    
    def __init__(
        self,
        strategy_id: str = "volatility_release",
        compression_threshold: float = 0.5,
        lookback_period: int = 20,
        atr_period: int = 14,
        time_decay_hours: int = 4,
    ):
        super().__init__(
            strategy_id=strategy_id,
            tier=WitnessTier.TIER_1,
            validity_window=60,
        )
        self.compression_threshold = compression_threshold
        self.lookback_period = lookback_period
        self.atr_period = atr_period
        self.time_decay_hours = time_decay_hours
        self._compression_start: datetime | None = None
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        """生成波动率释放 Claim"""
        if len(market_data) < self.lookback_period + self.atr_period:
            return None
        
        # 使用 analysis 模块检测压缩
        compression = detect_compression(
            market_data,
            threshold=self.compression_threshold,
            atr_period=self.atr_period,
            history_period=self.lookback_period,
        )
        
        # 检测压缩状态
        if compression.is_compressed:
            if self._compression_start is None:
                self._compression_start = utc_now()
                logger.debug(f"波动率压缩开始: ratio={compression.ratio:.2f}")
            return None
        
        # 检测释放（从压缩状态恢复）
        if self._compression_start is not None:
            # 计算时间衰减
            hours_compressed = (utc_now() - self._compression_start).total_seconds() / 3600
            time_factor = min(1.0, hours_compressed / self.time_decay_hours)
            
            # 判断方向
            recent_bars = market_data[-3:]
            direction = self._determine_direction(recent_bars)
            
            # 计算置信度
            confidence = self._calculate_confidence(compression.ratio, time_factor)
            
            # 重置压缩状态
            self._compression_start = None
            
            if confidence >= 0.6:
                logger.info(
                    f"波动率释放信号: direction={direction}, confidence={confidence:.2f}",
                    extra={"direction": direction, "confidence": confidence},
                )
                return self.create_claim(
                    claim_type=ClaimType.MARKET_ELIGIBLE,
                    confidence=confidence,
                    direction=direction,
                    constraints={
                        "compression_ratio": compression.ratio,
                        "time_factor": time_factor,
                        "signal_type": "volatility_release",
                    },
                )
        
        return None
    
    def _determine_direction(self, bars: list[MarketBar]) -> str:
        """判断方向"""
        if len(bars) < 2:
            return "long"
        
        price_change = bars[-1].close - bars[0].open
        return "long" if price_change > 0 else "short"
    
    def _calculate_confidence(self, compression_ratio: float, time_factor: float) -> float:
        """计算置信度"""
        # 压缩越深，释放信号越强
        compression_score = max(0, 1 - compression_ratio)
        
        # 时间因子加成
        base_confidence = 0.5 + compression_score * 0.3
        
        return min(0.95, base_confidence + time_factor * 0.1)
