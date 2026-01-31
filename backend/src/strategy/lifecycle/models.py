"""
BTC 自动交易系统 — 生命周期数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.enums import HealthGrade, WitnessTier
from src.common.models import Claim
from src.common.utils import utc_now


# 健康度 → 权重因子映射
HEALTH_FACTOR_MAP: dict[HealthGrade, float] = {
    HealthGrade.A: 1.2,
    HealthGrade.B: 1.0,
    HealthGrade.C: 0.7,
    HealthGrade.D: 0.5,
}


@dataclass
class WitnessWeight:
    """证人权重"""
    strategy_id: str
    base_weight: float = 1.0       # L1 配置 (0.5-2.0)
    health_factor: float = 1.0     # 健康度因子 (0.5-1.2)
    learning_factor: float = 1.0   # 自学习因子 (0.8-1.2)
    updated_at: datetime = field(default_factory=utc_now)
    
    @property
    def effective_weight(self) -> float:
        """有效权重 = 基础 × 健康度 × 学习因子"""
        return self.base_weight * self.health_factor * self.learning_factor
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "base_weight": self.base_weight,
            "health_factor": self.health_factor,
            "learning_factor": self.learning_factor,
            "effective_weight": self.effective_weight,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class StrategyStateRecord:
    """策略状态变更记录"""
    strategy_id: str
    status: str
    previous_status: str | None
    tier: WitnessTier | None
    changed_at: datetime
    reason: str
    changed_by: str  # "system" | "admin"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "status": self.status,
            "previous_status": self.previous_status,
            "tier": self.tier.value if self.tier else None,
            "changed_at": self.changed_at.isoformat(),
            "reason": self.reason,
            "changed_by": self.changed_by,
        }


@dataclass
class ShadowTradeRecord:
    """影子交易记录"""
    strategy_id: str
    claim: Claim
    timestamp: datetime
    market_price: float
    simulated_entry: float | None = None
    simulated_exit: float | None = None
    simulated_pnl: float | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "claim_type": self.claim.claim_type.value,
            "direction": self.claim.direction,
            "confidence": self.claim.confidence,
            "timestamp": self.timestamp.isoformat(),
            "market_price": self.market_price,
            "simulated_pnl": self.simulated_pnl,
        }


@dataclass
class ShadowPerformance:
    """影子运行绩效"""
    strategy_id: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    win_rate: float
    days_running: int
    first_trade_at: datetime | None
    last_trade_at: datetime | None
    
    @property
    def is_ready_for_promotion(self) -> bool:
        """是否满足晋升条件：运行 >= 7 天，胜率 >= 51%"""
        return self.days_running >= 7 and self.win_rate >= 0.51
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_pnl": self.total_pnl,
            "win_rate": self.win_rate,
            "days_running": self.days_running,
            "is_ready_for_promotion": self.is_ready_for_promotion,
        }
