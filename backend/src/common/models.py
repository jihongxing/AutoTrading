"""
BTC 自动交易系统 — 数据模型

使用 Pydantic v2，所有模型不可变（frozen=True）。
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .enums import (
    ClaimType,
    HealthGrade,
    OrderSide,
    OrderStatus,
    OrderType,
    RiskEventType,
    RiskLevel,
    WitnessStatus,
    WitnessTier,
)


def utc_now() -> datetime:
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc)


# ============================================================
# 策略层模型
# ============================================================

class Claim(BaseModel):
    """
    策略声明（策略唯一合法输出）
    
    策略只能输出 Claim，不能直接下单。
    """
    model_config = {"frozen": True}
    
    strategy_id: str
    claim_type: ClaimType
    confidence: float = Field(ge=0.0, le=1.0)
    validity_window: int = Field(gt=0, description="有效时间窗口（秒）")
    direction: str | None = Field(default=None, description="方向建议: long/short/none")
    constraints: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
    
    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str | None) -> str | None:
        if v is not None and v not in ("long", "short", "none"):
            raise ValueError("direction must be long/short/none")
        return v


class WitnessHealth(BaseModel):
    """证人健康度"""
    model_config = {"frozen": True}
    
    witness_id: str
    tier: WitnessTier
    status: WitnessStatus = WitnessStatus.ACTIVE
    grade: HealthGrade = HealthGrade.B
    win_rate: float = Field(ge=0.0, le=1.0)
    sample_count: int = Field(ge=0)
    sharpe_ratio: float = 0.0
    max_drawdown: float = Field(ge=0.0, le=1.0, default=0.0)
    weight: float = Field(ge=0.1, le=0.9, default=0.5)
    last_updated: datetime = Field(default_factory=utc_now)


# ============================================================
# 执行层模型
# ============================================================

class Order(BaseModel):
    """订单"""
    order_id: str
    symbol: str = "BTCUSDT"
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: float = Field(gt=0)
    price: float | None = None  # None = 市价单
    status: OrderStatus = OrderStatus.PENDING
    strategy_id: str
    timestamp: datetime = Field(default_factory=utc_now)


class ExecutionResult(BaseModel):
    """执行结果"""
    model_config = {"frozen": True}
    
    order_id: str
    status: OrderStatus
    executed_quantity: float
    executed_price: float
    slippage: float = 0.0
    commission: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)
    flags: list[str] = Field(default_factory=list)


# ============================================================
# 风控层模型
# ============================================================

class RiskEvent(BaseModel):
    """风险事件"""
    model_config = {"frozen": True}
    
    event_id: str
    event_type: RiskEventType
    level: RiskLevel
    description: str
    value: float | None = None  # 触发值
    threshold: float | None = None  # 阈值
    timestamp: datetime = Field(default_factory=utc_now)


class RiskCheckResult(BaseModel):
    """风控检查结果"""
    model_config = {"frozen": True}
    
    approved: bool
    level: RiskLevel
    reason: str | None = None
    events: list[RiskEvent] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


# ============================================================
# 数据层模型
# ============================================================

class MarketBar(BaseModel):
    """K 线数据"""
    model_config = {"frozen": True}
    
    ts: int = Field(description="UTC 毫秒时间戳")
    symbol: str = "BTCUSDT"
    interval: str = Field(description="1m/5m/15m/1h/4h/1d")
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float = 0.0
    trades: int = 0


class FundingRate(BaseModel):
    """资金费率"""
    model_config = {"frozen": True}
    
    ts: int
    symbol: str = "BTCUSDT"
    funding_rate: float
    mark_price: float
    index_price: float


class Liquidation(BaseModel):
    """清算数据"""
    model_config = {"frozen": True}
    
    ts: int
    symbol: str = "BTCUSDT"
    side: str  # LONG / SHORT
    quantity: float
    price: float
    usd_value: float
