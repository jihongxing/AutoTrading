"""
BTC 自动交易系统 — 风控证人（TIER 3）

具有一票否决权的风控证人。
"""

from src.common.enums import ClaimType, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar

from ..base import BaseStrategy

logger = get_logger(__name__)


class RiskSentinelWitness(BaseStrategy):
    """
    风控证人（TIER 3 否决证人）
    
    具有一票否决权：
    1. 仓位限制检查
    2. 回撤检查
    3. 连续亏损检查
    4. 极端波动检查
    """
    
    def __init__(
        self,
        strategy_id: str = "risk_sentinel",
        max_position_pct: float = 0.30,
        max_drawdown_pct: float = 0.20,
        max_consecutive_losses: int = 3,
        extreme_volatility_threshold: float = 0.05,
    ):
        super().__init__(
            strategy_id=strategy_id,
            tier=WitnessTier.TIER_3,
            validity_window=120,
        )
        self.max_position_pct = max_position_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.extreme_volatility_threshold = extreme_volatility_threshold
        
        # 状态跟踪
        self._current_position_pct: float = 0.0
        self._current_drawdown_pct: float = 0.0
        self._consecutive_losses: int = 0
    
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        """生成风控否决 Claim"""
        if not market_data:
            return None
        
        # 检查极端波动
        extreme_vol = self._check_extreme_volatility(market_data)
        if extreme_vol:
            logger.warning(
                f"风控否决: 极端波动 {extreme_vol:.2%}",
                extra={"reason": "extreme_volatility", "value": extreme_vol},
            )
            return self.create_claim(
                claim_type=ClaimType.EXECUTION_VETO,
                confidence=1.0,
                constraints={
                    "veto_reason": "extreme_volatility",
                    "volatility": extreme_vol,
                    "threshold": self.extreme_volatility_threshold,
                },
            )
        
        # 检查仓位限制
        if self._current_position_pct >= self.max_position_pct:
            logger.warning(
                f"风控否决: 仓位超限 {self._current_position_pct:.2%}",
                extra={"reason": "position_limit", "value": self._current_position_pct},
            )
            return self.create_claim(
                claim_type=ClaimType.EXECUTION_VETO,
                confidence=1.0,
                constraints={
                    "veto_reason": "position_limit_exceeded",
                    "current_position": self._current_position_pct,
                    "max_position": self.max_position_pct,
                },
            )
        
        # 检查回撤
        if self._current_drawdown_pct >= self.max_drawdown_pct:
            logger.warning(
                f"风控否决: 回撤超限 {self._current_drawdown_pct:.2%}",
                extra={"reason": "drawdown_limit", "value": self._current_drawdown_pct},
            )
            return self.create_claim(
                claim_type=ClaimType.EXECUTION_VETO,
                confidence=1.0,
                constraints={
                    "veto_reason": "drawdown_limit_exceeded",
                    "current_drawdown": self._current_drawdown_pct,
                    "max_drawdown": self.max_drawdown_pct,
                },
            )
        
        # 检查连续亏损
        if self._consecutive_losses >= self.max_consecutive_losses:
            logger.warning(
                f"风控否决: 连续亏损 {self._consecutive_losses} 次",
                extra={"reason": "consecutive_losses", "value": self._consecutive_losses},
            )
            return self.create_claim(
                claim_type=ClaimType.EXECUTION_VETO,
                confidence=1.0,
                constraints={
                    "veto_reason": "consecutive_losses_exceeded",
                    "consecutive_losses": self._consecutive_losses,
                    "max_consecutive_losses": self.max_consecutive_losses,
                },
            )
        
        return None
    
    def _check_extreme_volatility(self, market_data: list[MarketBar]) -> float | None:
        """检查极端波动"""
        if len(market_data) < 2:
            return None
        
        current = market_data[-1]
        prev = market_data[-2]
        
        if prev.close == 0:
            return None
        
        change_pct = abs(current.close - prev.close) / prev.close
        
        if change_pct >= self.extreme_volatility_threshold:
            return change_pct
        
        return None
    
    def update_position(self, position_pct: float) -> None:
        """更新当前仓位"""
        self._current_position_pct = position_pct
    
    def update_drawdown(self, drawdown_pct: float) -> None:
        """更新当前回撤"""
        self._current_drawdown_pct = drawdown_pct
    
    def record_trade_result(self, is_win: bool) -> None:
        """记录交易结果"""
        if is_win:
            self._consecutive_losses = 0
        else:
            self._consecutive_losses += 1
