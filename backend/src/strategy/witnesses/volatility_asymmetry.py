"""
BTC 自动交易系统 — 波动率不对称证人（TIER 2）

检测上下波动率不对称信号。
"""

import statistics

from src.common.enums import ClaimType, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar

from ..base import BaseStrategy

logger = get_logger(__name__)


class VolatilityAsymmetryWitness(BaseStrategy):
    """
    波动率不对称证人（TIER 2 辅助证人）
    
    检测上下波动率不对称：
    1. 上涨波动率 vs 下跌波动率
    2. 不对称程度
    3. 方向偏好
    """
    
    def __init__(
        self,
        strategy_id: str = "volatility_asymmetry",
        lookback_period: int = 24,
        asymmetry_threshold: float = 1.3,
    ):
        super().__init__(
            strategy_id=strategy_id,
            tier=WitnessTier.TIER_2,
            validity_window=30,
        )
        self.lookback_period = lookback_period
        self.asymmetry_threshold = asymmetry_threshold
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        """生成波动率不对称 Claim"""
        if len(market_data) < self.lookback_period:
            return None
        
        recent_bars = market_data[-self.lookback_period:]
        
        # 计算上涨和下跌波动率
        up_moves = []
        down_moves = []
        
        for i in range(1, len(recent_bars)):
            change = recent_bars[i].close - recent_bars[i - 1].close
            if change > 0:
                up_moves.append(change)
            elif change < 0:
                down_moves.append(abs(change))
        
        if not up_moves or not down_moves:
            return None
        
        up_vol = statistics.mean(up_moves)
        down_vol = statistics.mean(down_moves)
        
        if down_vol == 0:
            return None
        
        # 计算不对称比率
        asymmetry_ratio = up_vol / down_vol
        
        # 检测显著不对称
        if asymmetry_ratio > self.asymmetry_threshold:
            # 上涨波动率更大，偏向多头
            return self.create_claim(
                claim_type=ClaimType.REGIME_MATCHED,
                confidence=0.55,
                direction="long",
                constraints={
                    "asymmetry_ratio": asymmetry_ratio,
                    "up_volatility": up_vol,
                    "down_volatility": down_vol,
                    "signal_type": "volatility_asymmetry",
                },
            )
        elif asymmetry_ratio < 1 / self.asymmetry_threshold:
            # 下跌波动率更大，偏向空头
            return self.create_claim(
                claim_type=ClaimType.REGIME_MATCHED,
                confidence=0.55,
                direction="short",
                constraints={
                    "asymmetry_ratio": asymmetry_ratio,
                    "up_volatility": up_vol,
                    "down_volatility": down_vol,
                    "signal_type": "volatility_asymmetry",
                },
            )
        
        return None
