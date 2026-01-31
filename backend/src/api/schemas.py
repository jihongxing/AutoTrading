"""
BTC 自动交易系统 — API 响应模型

定义所有 API 响应的 Pydantic 模型。
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from src.common.enums import (
    ClaimType,
    HealthGrade,
    OrderSide,
    OrderStatus,
    OrderType,
    RiskLevel,
    SystemState,
    WitnessStatus,
    WitnessTier,
)
from src.core.state import TradeRegime

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    success: bool = True
    data: T | None = None
    error: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str
    message: str
    details: dict[str, Any] | None = None


# ========================================
# 系统状态响应
# ========================================

class StateResponse(BaseModel):
    """系统状态响应"""
    current_state: SystemState
    current_regime: TradeRegime | None = None
    is_trading_allowed: bool
    state_since: datetime
    risk_level: RiskLevel


class StateHistoryItem(BaseModel):
    """状态历史项"""
    state: SystemState
    timestamp: datetime
    reason: str | None = None
    triggered_by: str | None = None


class StateHistoryResponse(BaseModel):
    """状态历史响应"""
    items: list[StateHistoryItem]
    total: int


# ========================================
# 证人响应
# ========================================

class WitnessHealthResponse(BaseModel):
    """证人健康度响应"""
    witness_id: str
    tier: WitnessTier
    status: WitnessStatus
    grade: HealthGrade
    win_rate: float
    sample_count: int
    weight: float


class WitnessResponse(BaseModel):
    """证人响应"""
    witness_id: str
    tier: WitnessTier
    status: WitnessStatus
    is_active: bool
    validity_window: int
    health: WitnessHealthResponse | None = None


class WitnessListResponse(BaseModel):
    """证人列表响应"""
    witnesses: list[WitnessResponse]
    total: int
    active_count: int


# ========================================
# 风控响应
# ========================================

class RiskEventResponse(BaseModel):
    """风控事件响应"""
    event_id: str
    timestamp: datetime
    event_type: str
    severity: RiskLevel
    message: str
    details: dict[str, Any] | None = None


class RiskStatusResponse(BaseModel):
    """风控状态响应"""
    level: RiskLevel
    is_locked: bool
    lock_reason: str | None = None
    lock_since: datetime | None = None
    recent_events: list[RiskEventResponse]
    daily_loss: float
    current_drawdown: float


# ========================================
# 执行响应
# ========================================

class OrderResponse(BaseModel):
    """订单响应"""
    order_id: str
    client_order_id: str | None = None
    symbol: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    quantity: float
    filled_quantity: float
    price: float | None = None
    avg_price: float | None = None
    created_at: datetime
    updated_at: datetime | None = None


class OrderListResponse(BaseModel):
    """订单列表响应"""
    orders: list[OrderResponse]
    total: int


class PositionResponse(BaseModel):
    """仓位响应"""
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    leverage: int
    liquidation_price: float | None = None


class PositionListResponse(BaseModel):
    """仓位列表响应"""
    positions: list[PositionResponse]
    total_unrealized_pnl: float


# ========================================
# 数据响应
# ========================================

class MarketBarResponse(BaseModel):
    """K 线数据响应"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketBarsResponse(BaseModel):
    """K 线列表响应"""
    symbol: str
    interval: str
    bars: list[MarketBarResponse]


class FundingRateResponse(BaseModel):
    """资金费率响应"""
    timestamp: datetime
    symbol: str
    funding_rate: float
    next_funding_time: datetime | None = None


class LiquidationResponse(BaseModel):
    """清算数据响应"""
    timestamp: datetime
    symbol: str
    side: str
    quantity: float
    price: float


# ========================================
# 学习响应
# ========================================

class SuggestionResponse(BaseModel):
    """优化建议响应"""
    suggestion_id: str
    param_name: str
    current_value: float
    suggested_value: float
    action: str
    reason: str
    confidence: float
    requires_approval: bool


class LearningReportResponse(BaseModel):
    """学习报告响应"""
    period: str
    timestamp: datetime
    start_time: datetime
    end_time: datetime
    total_trades: int
    win_rate: float
    avg_pnl: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    suggestions_count: int
    pending_approvals: int


class SuggestionListResponse(BaseModel):
    """建议列表响应"""
    suggestions: list[SuggestionResponse]
    total: int
    pending_count: int


# ========================================
# 请求模型
# ========================================

class ForceLockRequest(BaseModel):
    """强制锁定请求"""
    reason: str
    duration_hours: int | None = None


class UnlockRequest(BaseModel):
    """解锁请求"""
    reason: str
    override_code: str | None = None


class ApproveRequest(BaseModel):
    """审批请求"""
    suggestion_ids: list[str]
    approved: bool
    comment: str | None = None
