"""
BTC 自动交易系统 — 用户执行上下文

封装单用户的完整执行环境。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.enums import OrderSide, OrderStatus, OrderType
from src.common.logging import get_logger
from src.common.models import Claim, Order
from src.common.utils import utc_now
from src.core.execution.exchange.base import ExchangeOrderResult, Position
from src.core.execution.exchange.binance import BinanceClient

from .crypto import decrypt_api_key
from .models import User, UserExchangeConfig, UserRiskState

logger = get_logger(__name__)


@dataclass
class TradingSignal:
    """交易信号"""
    signal_id: str
    symbol: str
    direction: str  # "long" / "short"
    confidence: float
    position_pct: float  # 建议仓位比例
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    source_claims: list[Claim] = field(default_factory=list)
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class UserExecutionResult:
    """用户执行结果"""
    user_id: str
    signal_id: str
    success: bool
    order_id: str | None = None
    executed_quantity: float = 0.0
    executed_price: float = 0.0
    error: str | None = None
    timestamp: datetime = field(default_factory=utc_now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "signal_id": self.signal_id,
            "success": self.success,
            "order_id": self.order_id,
            "executed_quantity": self.executed_quantity,
            "executed_price": self.executed_price,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class UserContext:
    """
    用户执行上下文
    
    封装单用户的完整执行环境，包括：
    - 交易所客户端
    - 风控状态
    - 仓位管理
    """
    
    def __init__(
        self,
        user: User,
        config: UserExchangeConfig,
        risk_state: UserRiskState,
    ):
        self.user = user
        self.config = config
        self.risk_state = risk_state
        
        self._client: BinanceClient | None = None
        self._initialized = False
        self._last_balance: float = 0.0
        self._peak_balance: float = 0.0
    
    @property
    def user_id(self) -> str:
        return self.user.user_id
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def is_tradeable(self) -> bool:
        """是否可交易"""
        return (
            self._initialized
            and self.user.is_active
            and not self.user.is_trial_expired
            and self.config.is_valid
            and not self.risk_state.is_locked
        )
    
    async def initialize(self) -> bool:
        """
        初始化上下文
        
        创建交易所客户端并连接。
        """
        if self._initialized:
            return True
        
        try:
            # 解密 API Key
            api_key = decrypt_api_key(self.config.api_key_encrypted)
            api_secret = decrypt_api_key(self.config.api_secret_encrypted)
            
            if not api_key or not api_secret:
                logger.error(f"用户 {self.user_id} API Key 为空")
                return False
            
            # 创建客户端
            self._client = BinanceClient(
                api_key=api_key,
                api_secret=api_secret,
                testnet=self.config.testnet,
            )
            
            await self._client.connect()
            
            # 设置杠杆
            await self._client.set_leverage("BTCUSDT", self.config.leverage)
            
            # 获取初始余额
            self._last_balance = await self._client.get_balance()
            self._peak_balance = self._last_balance
            
            self._initialized = True
            logger.info(f"用户上下文已初始化: {self.user_id}, balance={self._last_balance}")
            return True
            
        except Exception as e:
            logger.error(f"用户上下文初始化失败: {self.user_id}, error={e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭上下文"""
        if self._client:
            await self._client.disconnect()
            self._client = None
        self._initialized = False
        logger.info(f"用户上下文已关闭: {self.user_id}")
    
    async def execute_signal(self, signal: TradingSignal) -> UserExecutionResult:
        """
        执行交易信号
        
        Args:
            signal: 交易信号
        
        Returns:
            执行结果
        """
        if not self.is_tradeable:
            return UserExecutionResult(
                user_id=self.user_id,
                signal_id=signal.signal_id,
                success=False,
                error="用户不可交易",
            )
        
        try:
            # 风控检查
            risk_ok, risk_msg = await self.check_risk()
            if not risk_ok:
                return UserExecutionResult(
                    user_id=self.user_id,
                    signal_id=signal.signal_id,
                    success=False,
                    error=f"风控拒绝: {risk_msg}",
                )
            
            # 计算仓位
            balance = await self.get_balance()
            position_pct = min(signal.position_pct, self.config.max_position_pct)
            position_value = balance * position_pct
            
            # 获取当前价格
            price = await self._client.get_ticker_price(signal.symbol)
            if price <= 0:
                return UserExecutionResult(
                    user_id=self.user_id,
                    signal_id=signal.signal_id,
                    success=False,
                    error="无法获取价格",
                )
            
            # 计算数量
            quantity = position_value / price
            quantity = round(quantity, 3)  # Binance 精度
            
            if quantity <= 0:
                return UserExecutionResult(
                    user_id=self.user_id,
                    signal_id=signal.signal_id,
                    success=False,
                    error="计算数量为 0",
                )
            
            # 创建订单
            order = Order(
                order_id=f"{self.user_id}_{signal.signal_id}",
                symbol=signal.symbol,
                side=OrderSide.BUY if signal.direction == "long" else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=quantity,
            )
            
            # 下单
            result = await self._client.place_order(order)
            
            if result.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
                logger.info(
                    f"用户 {self.user_id} 订单成交: {order.order_id}, "
                    f"qty={result.executed_quantity}, price={result.executed_price}"
                )
                return UserExecutionResult(
                    user_id=self.user_id,
                    signal_id=signal.signal_id,
                    success=True,
                    order_id=order.order_id,
                    executed_quantity=result.executed_quantity,
                    executed_price=result.executed_price,
                )
            else:
                return UserExecutionResult(
                    user_id=self.user_id,
                    signal_id=signal.signal_id,
                    success=False,
                    order_id=order.order_id,
                    error=f"订单状态: {result.status.value}",
                )
                
        except Exception as e:
            logger.error(f"用户 {self.user_id} 执行失败: {e}")
            return UserExecutionResult(
                user_id=self.user_id,
                signal_id=signal.signal_id,
                success=False,
                error=str(e),
            )
    
    async def check_risk(self) -> tuple[bool, str]:
        """
        检查风控
        
        Returns:
            (是否通过, 错误信息)
        """
        # 检查风控锁定
        if self.risk_state.is_locked:
            return False, self.risk_state.locked_reason or "风控锁定"
        
        # 检查回撤
        if self.risk_state.current_drawdown >= 0.20:
            self.risk_state.lock("回撤超限")
            return False, "回撤超限"
        
        # 检查日亏损
        if self.risk_state.daily_loss >= 0.03:
            self.risk_state.lock("日亏损超限")
            return False, "日亏损超限"
        
        # 检查连续亏损
        if self.risk_state.consecutive_losses >= 3:
            self.risk_state.lock("连续亏损")
            return False, "连续亏损"
        
        return True, ""
    
    async def get_balance(self) -> float:
        """获取余额"""
        if not self._client:
            return 0.0
        
        balance = await self._client.get_balance()
        self._last_balance = balance
        
        # 更新峰值和回撤
        if balance > self._peak_balance:
            self._peak_balance = balance
        
        if self._peak_balance > 0:
            self.risk_state.current_drawdown = (self._peak_balance - balance) / self._peak_balance
        
        return balance
    
    async def get_position(self, symbol: str) -> Position:
        """获取仓位"""
        if not self._client:
            return Position(symbol=symbol, side="NONE", quantity=0, entry_price=0)
        
        return await self._client.get_position(symbol)
    
    async def get_all_positions(self) -> list[Position]:
        """获取所有仓位"""
        if not self._client:
            return []
        
        return await self._client.get_all_positions()
    
    async def close_position(self, symbol: str) -> UserExecutionResult:
        """平仓"""
        if not self._client:
            return UserExecutionResult(
                user_id=self.user_id,
                signal_id="close",
                success=False,
                error="客户端未初始化",
            )
        
        try:
            position = await self._client.get_position(symbol)
            
            if position.quantity == 0:
                return UserExecutionResult(
                    user_id=self.user_id,
                    signal_id="close",
                    success=True,
                    error="无持仓",
                )
            
            # 反向下单平仓
            side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
            
            order = Order(
                order_id=f"{self.user_id}_close_{utc_now().timestamp()}",
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=position.quantity,
            )
            
            result = await self._client.place_order(order)
            
            return UserExecutionResult(
                user_id=self.user_id,
                signal_id="close",
                success=result.status == OrderStatus.FILLED,
                order_id=order.order_id,
                executed_quantity=result.executed_quantity,
                executed_price=result.executed_price,
            )
            
        except Exception as e:
            return UserExecutionResult(
                user_id=self.user_id,
                signal_id="close",
                success=False,
                error=str(e),
            )
    
    def record_trade_result(self, pnl: float) -> None:
        """记录交易结果"""
        if pnl >= 0:
            self.risk_state.record_win(pnl)
        else:
            self.risk_state.record_loss(abs(pnl))
