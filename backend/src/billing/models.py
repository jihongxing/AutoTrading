"""
BTC 自动交易系统 — 计费数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.utils import utc_now
from src.user.models import SubscriptionPlan


@dataclass
class UserProfit:
    """用户收益记录"""
    user_id: str
    trade_id: str
    symbol: str
    side: str  # BUY/SELL
    realized_pnl: float
    fee_rate: float
    platform_fee: float
    net_profit: float
    timestamp: datetime = field(default_factory=utc_now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side,
            "realized_pnl": self.realized_pnl,
            "fee_rate": self.fee_rate,
            "platform_fee": self.platform_fee,
            "net_profit": self.net_profit,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ProfitSummary:
    """收益汇总"""
    user_id: str
    period: str  # daily/weekly/monthly
    start_date: datetime
    end_date: datetime
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    platform_fees: float = 0.0
    user_net_profit: float = 0.0
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "period": self.period,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "net_pnl": self.net_pnl,
            "platform_fees": self.platform_fees,
            "user_net_profit": self.user_net_profit,
            "win_rate": self.win_rate,
        }


@dataclass
class PlanConfig:
    """订阅计划配置"""
    plan: SubscriptionPlan
    fee_rate: float
    max_position_pct: float
    monthly_price: float
    trial_days: int
    
    @classmethod
    def from_plan(cls, plan: SubscriptionPlan) -> "PlanConfig":
        from src.user.models import PLAN_CONFIG
        config = PLAN_CONFIG[plan]
        return cls(
            plan=plan,
            fee_rate=config["fee_rate"],
            max_position_pct=config["max_position_pct"],
            monthly_price=config["monthly_price"],
            trial_days=config["trial_days"],
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.value,
            "fee_rate": self.fee_rate,
            "max_position_pct": self.max_position_pct,
            "monthly_price": self.monthly_price,
            "trial_days": self.trial_days,
        }
