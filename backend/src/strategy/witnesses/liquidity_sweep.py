"""
BTC 自动交易系统 — 流动性收割窗口证人（TIER 2）

检测流动性收割信号。
"""

import statistics

from src.common.enums import ClaimType, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar

from ..base import BaseStrategy

logger = get_logger(__name__)


class LiquiditySweepWitness(BaseStrategy):
    """
    流动性收割窗口证人（TIER 2 辅助证人）
    
    检测流动性收割信号：
    1. 止损猎杀检测
    2. 流动性池识别
    3. 反转信号
    """
    
    def __init__(
        self,
        strategy_id: str = "liquidity_sweep",
        lookback_period: int = 48,
        sweep_threshold: float = 0.02,
        reversal_threshold: float = 0.5,
    ):
        super().__init__(
            strategy_id=strategy_id,
            tier=WitnessTier.TIER_2,
            validity_window=30,
        )
        self.lookback_period = lookback_period
        self.sweep_threshold = sweep_threshold
        self.reversal_threshold = reversal_threshold
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        """生成流动性收割 Claim"""
        if len(market_data) < self.lookback_period:
            return None
        
        recent_bars = market_data[-self.lookback_period:]
        current_bar = market_data[-1]
        
        # 识别流动性池（前期高低点）
        highs = [b.high for b in recent_bars[:-1]]
        lows = [b.low for b in recent_bars[:-1]]
        
        liquidity_high = max(highs)
        liquidity_low = min(lows)
        
        # 检测向上扫荡
        if current_bar.high > liquidity_high:
            sweep_depth = (current_bar.high - liquidity_high) / liquidity_high
            
            if sweep_depth >= self.sweep_threshold:
                # 检测反转
                reversal = self._detect_reversal(current_bar, "up")
                
                if reversal:
                    return self.create_claim(
                        claim_type=ClaimType.MARKET_ELIGIBLE,
                        confidence=0.55,
                        direction="short",
                        constraints={
                            "sweep_type": "upside_sweep",
                            "sweep_depth": sweep_depth,
                            "liquidity_level": liquidity_high,
                            "signal_type": "liquidity_sweep",
                        },
                    )
        
        # 检测向下扫荡
        if current_bar.low < liquidity_low:
            sweep_depth = (liquidity_low - current_bar.low) / liquidity_low
            
            if sweep_depth >= self.sweep_threshold:
                # 检测反转
                reversal = self._detect_reversal(current_bar, "down")
                
                if reversal:
                    return self.create_claim(
                        claim_type=ClaimType.MARKET_ELIGIBLE,
                        confidence=0.55,
                        direction="long",
                        constraints={
                            "sweep_type": "downside_sweep",
                            "sweep_depth": sweep_depth,
                            "liquidity_level": liquidity_low,
                            "signal_type": "liquidity_sweep",
                        },
                    )
        
        return None
    
    def _detect_reversal(self, bar: MarketBar, sweep_direction: str) -> bool:
        """检测反转"""
        bar_range = bar.high - bar.low
        if bar_range == 0:
            return False
        
        if sweep_direction == "up":
            # 向上扫荡后，收盘价应该回落
            upper_wick = bar.high - max(bar.open, bar.close)
            return upper_wick / bar_range >= self.reversal_threshold
        else:
            # 向下扫荡后，收盘价应该回升
            lower_wick = min(bar.open, bar.close) - bar.low
            return lower_wick / bar_range >= self.reversal_threshold
