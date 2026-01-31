"""
BTC 自动交易系统 — 微结构异常证人（TIER 2）

检测市场微结构异常信号。
"""

from src.analysis import detect_gap, detect_volume_anomaly
from src.common.enums import ClaimType, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar

from ..base import BaseStrategy

logger = get_logger(__name__)


class MicrostructureWitness(BaseStrategy):
    """
    微结构异常证人（TIER 2 辅助证人）
    
    检测市场微结构异常：
    1. 成交量异常
    2. 价格跳空
    3. 订单流不平衡
    """
    
    def __init__(
        self,
        strategy_id: str = "microstructure",
        lookback_period: int = 24,
        volume_threshold: float = 2.0,
        gap_threshold: float = 0.005,
    ):
        super().__init__(
            strategy_id=strategy_id,
            tier=WitnessTier.TIER_2,
            validity_window=30,
        )
        self.lookback_period = lookback_period
        self.volume_threshold = volume_threshold
        self.gap_threshold = gap_threshold
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        """生成微结构异常 Claim"""
        if len(market_data) < self.lookback_period:
            return None
        
        prev_bar = market_data[-2]
        current_bar = market_data[-1]
        
        # 使用 analysis 模块检测成交量异常
        volume_result = detect_volume_anomaly(
            market_data,
            surge_threshold=self.volume_threshold,
            lookback=self.lookback_period,
        )
        
        # 使用 analysis 模块检测价格跳空
        gap_result = detect_gap(prev_bar, current_bar, threshold=self.gap_threshold)
        
        # 综合判断
        if volume_result.is_anomaly and gap_result.has_gap:
            direction = "long" if gap_result.direction == "up" else "short"
            confidence = 0.6
            
            return self.create_claim(
                claim_type=ClaimType.REGIME_MATCHED,
                confidence=confidence,
                direction=direction,
                constraints={
                    "volume_ratio": volume_result.ratio,
                    "gap_size": gap_result.gap_pct,
                    "signal_type": "microstructure",
                },
            )
        elif volume_result.is_anomaly and volume_result.anomaly_type == "surge":
            # 仅成交量异常
            return self.create_claim(
                claim_type=ClaimType.REGIME_MATCHED,
                confidence=0.52,
                constraints={
                    "volume_ratio": volume_result.ratio,
                    "anomaly_type": "volume_spike",
                    "signal_type": "microstructure",
                },
            )
        
        return None
