"""
BTC 自动交易系统 — 时间结构优势证人（TIER 2）

检测时间结构优势信号。
"""

from src.analysis import get_session_info, is_trading_favorable
from src.common.enums import ClaimType, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar

from ..base import BaseStrategy

logger = get_logger(__name__)


class TimeStructureWitness(BaseStrategy):
    """
    时间结构优势证人（TIER 2 辅助证人）
    
    检测时间结构优势：
    1. 高波动时段识别
    2. 低流动性时段规避
    3. 周期性模式
    """
    
    def __init__(
        self,
        strategy_id: str = "time_structure",
        volatility_boost: float = 0.1,
        liquidity_penalty: float = 0.15,
    ):
        super().__init__(
            strategy_id=strategy_id,
            tier=WitnessTier.TIER_2,
            validity_window=30,
        )
        self.volatility_boost = volatility_boost
        self.liquidity_penalty = liquidity_penalty
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        """生成时间结构 Claim"""
        if not market_data:
            return None
        
        # 使用 analysis 模块获取时段信息
        session_info = get_session_info()
        
        # 周末流动性较低
        if session_info.is_weekend:
            return self.create_claim(
                claim_type=ClaimType.MARKET_NOT_ELIGIBLE,
                confidence=0.6,
                constraints={
                    "reason": "weekend_low_liquidity",
                    "signal_type": "time_structure",
                },
            )
        
        # 低流动性时段
        if session_info.is_low_liquidity:
            return self.create_claim(
                claim_type=ClaimType.MARKET_NOT_ELIGIBLE,
                confidence=0.55,
                constraints={
                    "reason": "low_liquidity_hour",
                    "hour": session_info.hour,
                    "signal_type": "time_structure",
                },
            )
        
        # 高波动时段
        if session_info.is_high_volatility:
            return self.create_claim(
                claim_type=ClaimType.REGIME_MATCHED,
                confidence=0.6,
                constraints={
                    "reason": "high_volatility_hour",
                    "hour": session_info.hour,
                    "volatility_boost": self.volatility_boost,
                    "signal_type": "time_structure",
                },
            )
        
        return None
