"""
BTC 自动交易系统 — Trade Regime 管理

管理交易范式的识别和输出。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.common.logging import get_logger
from src.common.utils import utc_now

logger = get_logger(__name__)


class TradeRegime(str, Enum):
    """交易范式"""
    VOLATILITY_EXPANSION = "volatility_expansion"      # 波动率扩张
    RANGE_STRUCTURE_BREAK = "range_structure_break"    # 区间结构突破
    LIQUIDITY_SWEEP = "liquidity_sweep"                # 流动性扫荡
    TREND_CONTINUATION = "trend_continuation"          # 趋势延续
    MEAN_REVERSION = "mean_reversion"                  # 均值回归
    NO_REGIME = "no_regime"                            # 无明确范式


@dataclass(frozen=True)
class RegimeConstraints:
    """范式约束"""
    max_position_ratio: float = 0.05
    max_holding_minutes: int = 60
    stop_loss_ratio: float = 0.02
    take_profit_ratio: float = 0.04


# 范式默认约束
REGIME_CONSTRAINTS: dict[TradeRegime, RegimeConstraints] = {
    TradeRegime.VOLATILITY_EXPANSION: RegimeConstraints(
        max_position_ratio=0.03,
        max_holding_minutes=30,
        stop_loss_ratio=0.015,
        take_profit_ratio=0.03,
    ),
    TradeRegime.RANGE_STRUCTURE_BREAK: RegimeConstraints(
        max_position_ratio=0.05,
        max_holding_minutes=120,
        stop_loss_ratio=0.02,
        take_profit_ratio=0.05,
    ),
    TradeRegime.LIQUIDITY_SWEEP: RegimeConstraints(
        max_position_ratio=0.02,
        max_holding_minutes=15,
        stop_loss_ratio=0.01,
        take_profit_ratio=0.02,
    ),
    TradeRegime.TREND_CONTINUATION: RegimeConstraints(
        max_position_ratio=0.05,
        max_holding_minutes=240,
        stop_loss_ratio=0.025,
        take_profit_ratio=0.06,
    ),
    TradeRegime.MEAN_REVERSION: RegimeConstraints(
        max_position_ratio=0.03,
        max_holding_minutes=60,
        stop_loss_ratio=0.015,
        take_profit_ratio=0.03,
    ),
    TradeRegime.NO_REGIME: RegimeConstraints(
        max_position_ratio=0.02,
        max_holding_minutes=30,
        stop_loss_ratio=0.01,
        take_profit_ratio=0.02,
    ),
}


class RegimeOutput(BaseModel):
    """范式输出"""
    model_config = {"frozen": True}
    
    regime: TradeRegime
    confidence: float = Field(ge=0.0, le=1.0)
    constraints: RegimeConstraints
    valid_until: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class RegimeManager:
    """
    Trade Regime 管理器
    
    管理当前交易范式和约束输出。
    """
    
    def __init__(self):
        self._current_regime: TradeRegime = TradeRegime.NO_REGIME
        self._regime_confidence: float = 0.0
        self._regime_set_at: datetime = utc_now()
        self._validity_minutes: int = 15
    
    @property
    def current_regime(self) -> TradeRegime:
        """当前范式"""
        return self._current_regime
    
    @property
    def is_valid(self) -> bool:
        """范式是否有效"""
        if self._current_regime == TradeRegime.NO_REGIME:
            return False
        elapsed = (utc_now() - self._regime_set_at).total_seconds() / 60
        return elapsed < self._validity_minutes
    
    def set_regime(
        self,
        regime: TradeRegime,
        confidence: float,
        validity_minutes: int = 15,
    ) -> None:
        """
        设置当前范式
        
        Args:
            regime: 交易范式
            confidence: 置信度
            validity_minutes: 有效时间（分钟）
        """
        self._current_regime = regime
        self._regime_confidence = confidence
        self._regime_set_at = utc_now()
        self._validity_minutes = validity_minutes
        
        logger.info(
            f"设置交易范式: {regime.value}, 置信度: {confidence:.2%}",
            extra={"regime": regime.value, "confidence": confidence},
        )
    
    def clear_regime(self) -> None:
        """清除当前范式"""
        self._current_regime = TradeRegime.NO_REGIME
        self._regime_confidence = 0.0
        logger.info("清除交易范式")
    
    def get_output(self) -> RegimeOutput | None:
        """
        获取范式输出
        
        Returns:
            范式输出，如果无有效范式则返回 None
        """
        if not self.is_valid:
            return None
        
        from datetime import timedelta
        
        constraints = REGIME_CONSTRAINTS.get(
            self._current_regime,
            REGIME_CONSTRAINTS[TradeRegime.NO_REGIME],
        )
        
        return RegimeOutput(
            regime=self._current_regime,
            confidence=self._regime_confidence,
            constraints=constraints,
            valid_until=self._regime_set_at + timedelta(minutes=self._validity_minutes),
        )
    
    def get_constraints(self) -> RegimeConstraints:
        """获取当前约束"""
        return REGIME_CONSTRAINTS.get(
            self._current_regime,
            REGIME_CONSTRAINTS[TradeRegime.NO_REGIME],
        )
