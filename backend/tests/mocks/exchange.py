"""Mock 交易所客户端"""

from src.common.enums import OrderStatus
from src.common.models import Order
from src.core.execution.exchange.base import ExchangeClient, ExchangeOrderResult, Position


class MockExchangeClient(ExchangeClient):
    """Mock 交易所客户端，用于测试"""
    
    def __init__(self):
        self._connected = False
        self._orders: dict[str, Order] = {}
        self._position = Position(
            symbol="BTCUSDT",
            side="NONE",
            quantity=0,
            entry_price=0,
        )
        self._balance = 100000.0
        self._should_fail = False
        self._fill_price_offset = 0.0
    
    @property
    def name(self) -> str:
        return "mock"
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self) -> None:
        self._connected = True
    
    async def disconnect(self) -> None:
        self._connected = False
    
    async def place_order(self, order: Order) -> ExchangeOrderResult:
        if self._should_fail:
            raise RuntimeError("Mock 下单失败")
        
        self._orders[order.order_id] = order
        
        executed_price = (order.price or 50000.0) + self._fill_price_offset
        
        return ExchangeOrderResult(
            order_id=order.order_id,
            exchange_order_id=f"mock_{order.order_id}",
            status=OrderStatus.FILLED,
            executed_quantity=order.quantity,
            executed_price=executed_price,
            commission=executed_price * order.quantity * 0.0004,
        )
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        # 测试场景：总是返回成功（模拟撤销待处理订单）
        if order_id in self._orders:
            del self._orders[order_id]
        return True
    
    async def get_order_status(self, order_id: str, symbol: str) -> OrderStatus:
        if order_id in self._orders:
            return OrderStatus.FILLED
        return OrderStatus.PENDING
    
    async def get_position(self, symbol: str) -> Position:
        return self._position
    
    async def get_balance(self) -> float:
        return self._balance
    
    # 测试辅助方法
    def set_should_fail(self, should_fail: bool) -> None:
        self._should_fail = should_fail
    
    def set_position(self, position: Position) -> None:
        self._position = position
    
    def set_balance(self, balance: float) -> None:
        self._balance = balance
    
    def set_fill_price_offset(self, offset: float) -> None:
        self._fill_price_offset = offset
