"""
BTC 自动交易系统 — 风控基类

定义风控检查器接口和上下文模型。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.common.enums import RiskLevel
from src.common.models import RiskCheckResult, RiskEvent, WitnessHealth
from src.common.utils import utc_now


class TradeRecord(BaseModel):
    """交易记录"""
    model_config = {"frozen": True}
    
    trade_id: str
    strategy_id: str
    direction: str
    quantity: float
    entry_price: float
    exit_price: float | None = None
    pnl: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


class RiskContext(BaseModel):
    """
    风控上下文
    
    包含风控检查所需的所有信息。
    """
    # 账户状态
    equity: float = Field(gt=0, description="账户权益")
    initial_equity: float = Field(gt=0, description="初始权益")
    drawdown: float = Field(ge=0, le=1, description="当前回撤")
    daily_pnl: float = Field(description="当日盈亏")
    weekly_pnl: float = Field(default=0.0, description="本周盈亏")
    
    # 交易状态
    consecutive_losses: int = Field(ge=0, default=0)
    current_position: float = Field(ge=0, default=0)
    recent_trades: list[TradeRecord] = Field(default_factory=list)
    
    # 证人状态
    witness_health: dict[str, WitnessHealth] = Field(default_factory=dict)
    
    # 执行状态
    recent_slippages: list[float] = Field(default_factory=list)
    recent_fill_rates: list[float] = Field(default_factory=list)
    recent_latencies: list[int] = Field(default_factory=list)
    
    # 系统状态
    data_delay_ms: int = Field(default=0)
    last_heartbeat: datetime | None = None
    
    # 请求信息
    requested_position: float = Field(default=0.0)
    requested_direction: str | None = None
    
    @property
    def drawdown_ratio(self) -> float:
        """计算回撤比例"""
        if self.initial_equity <= 0:
            return 0.0
        return (self.initial_equity - self.equity) / self.initial_equity
    
    @property
    def daily_loss_ratio(self) -> float:
        """计算当日亏损比例"""
        if self.equity <= 0:
            return 0.0
        return -self.daily_pnl / self.equity if self.daily_pnl < 0 else 0.0


class RiskChecker(ABC):
    """
    风控检查器基类
    
    所有风险域检查器必须继承此类。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """检查器名称"""
        pass
    
    @abstractmethod
    async def check(self, context: RiskContext) -> RiskCheckResult:
        """
        执行风控检查
        
        Args:
            context: 风控上下文
        
        Returns:
            风控检查结果
        """
        pass
    
    def _create_event(
        self,
        event_type: str,
        level: RiskLevel,
        description: str,
        value: float | None = None,
        threshold: float | None = None,
    ) -> RiskEvent:
        """创建风控事件"""
        from src.common.enums import RiskEventType
        import uuid
        
        return RiskEvent(
            event_id=str(uuid.uuid4()),
            event_type=RiskEventType(event_type),
            level=level,
            description=description,
            value=value,
            threshold=threshold,
        )
    
    def _approve(self, level: RiskLevel = RiskLevel.NORMAL) -> RiskCheckResult:
        """返回批准结果"""
        return RiskCheckResult(approved=True, level=level)
    
    def _reject(
        self,
        level: RiskLevel,
        reason: str,
        events: list[RiskEvent] | None = None,
    ) -> RiskCheckResult:
        """返回拒绝结果"""
        return RiskCheckResult(
            approved=False,
            level=level,
            reason=reason,
            events=events or [],
        )
