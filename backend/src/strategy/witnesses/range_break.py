"""
BTC 自动交易系统 — 区间破坏证人（TIER 1）

检测价格区间突破信号。
"""

from src.analysis import detect_range, RangeResult
from src.common.enums import ClaimType, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar

from ..base import BaseStrategy

logger = get_logger(__name__)


class RangeBreakWitness(BaseStrategy):
    """
    区间破坏证人（TIER 1 核心证人）
    
    检测价格区间突破：
    1. 区间识别（高低点收敛）
    2. 突破确认（价格突破区间边界）
    3. 假突破过滤
    """
    
    def __init__(
        self,
        strategy_id: str = "range_break",
        lookback_period: int = 48,
        min_range_duration: int = 12,
        breakout_threshold: float = 0.01,
        confirmation_bars: int = 2,
    ):
        super().__init__(
            strategy_id=strategy_id,
            tier=WitnessTier.TIER_1,
            validity_window=60,
        )
        self.lookback_period = lookback_period
        self.min_range_duration = min_range_duration
        self.breakout_threshold = breakout_threshold
        self.confirmation_bars = confirmation_bars
        self._current_range: RangeResult | None = None
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        """生成区间突破 Claim"""
        if len(market_data) < self.lookback_period:
            return None
        
        # 使用 analysis 模块检测区间
        range_result = detect_range(
            market_data,
            lookback=self.lookback_period,
            max_width_pct=0.05,
            min_touches=2,
        )
        
        if not range_result.is_ranging:
            self._current_range = None
            return None
        
        self._current_range = range_result
        
        # 检测突破
        current_price = market_data[-1].close
        breakout = self._detect_breakout(current_price, range_result)
        
        if breakout is None:
            return None
        
        direction, strength = breakout
        
        # 确认突破（检查最近几根 K 线）
        if not self._confirm_breakout(
            market_data[-self.confirmation_bars:], range_result, direction
        ):
            return None
        
        # 计算置信度
        confidence = self._calculate_confidence(range_result, strength)
        
        logger.info(
            f"区间突破信号: direction={direction}, confidence={confidence:.2f}",
            extra={
                "direction": direction,
                "confidence": confidence,
                "range_width": range_result.width,
            },
        )
        
        return self.create_claim(
            claim_type=ClaimType.MARKET_ELIGIBLE,
            confidence=confidence,
            direction=direction,
            constraints={
                "range_high": range_result.high,
                "range_low": range_result.low,
                "range_duration": range_result.duration,
                "breakout_strength": strength,
                "signal_type": "range_break",
            },
        )
    
    def _detect_breakout(
        self, current_price: float, range_result: RangeResult
    ) -> tuple[str, float] | None:
        """检测突破"""
        threshold = range_result.width * self.breakout_threshold
        
        # 向上突破
        if current_price > range_result.high + threshold:
            strength = (current_price - range_result.high) / range_result.width
            return ("long", strength)
        
        # 向下突破
        if current_price < range_result.low - threshold:
            strength = (range_result.low - current_price) / range_result.width
            return ("short", strength)
        
        return None
    
    def _confirm_breakout(
        self, bars: list[MarketBar], range_result: RangeResult, direction: str
    ) -> bool:
        """确认突破（过滤假突破）"""
        if len(bars) < self.confirmation_bars:
            return False
        
        if direction == "long":
            return all(b.close > range_result.high for b in bars)
        else:
            return all(b.close < range_result.low for b in bars)
    
    def _calculate_confidence(self, range_result: RangeResult, strength: float) -> float:
        """计算置信度"""
        # 区间持续时间越长，突破越可靠
        duration_factor = min(1.0, range_result.duration / 48)
        
        # 突破强度
        strength_factor = min(1.0, strength)
        
        base_confidence = 0.55
        return min(0.95, base_confidence + duration_factor * 0.2 + strength_factor * 0.15)
