"""
BTC 自动交易系统 — 交易所基类

定义交易所客户端接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.enums import OrderSide, OrderStatus, OrderType
from src.common.models import Order
from src.common.utils import utc_now


@dataclass
class Position:
    """仓位信息"""
    symbol: str
    side: str  # LONG / SHORT / NONE
    quantity: float
    entry_price: float
    unrealized_pnl: float = 0.0
    leverage: int = 1
    margin: float = 0.0
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class ExchangeOrderResult:
    """交易所订单结果"""
    order_id: str
    exchange_order_id: str
    status: OrderStatus
    executed_quantity: float
    executed_price: float
    commission: float = 0.0
    timestamp: datetime = field(default_factory=utc_now)
    raw_response: dict[str, Any] = field(default_factory=dict)


class ExchangeClient(ABC):
    """
    交易所客户端抽象基类
    
    所有交易所实现必须继承此类。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """交易所名称"""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """是否已连接"""
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """建立连接"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    async def place_order(self, order: Order) -> ExchangeOrderResult:
        """
        下单
        
        Args:
            order: 订单
        
        Returns:
            交易所订单结果
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        撤单
        
        Args:
            order_id: 订单 ID
            symbol: 交易对
        
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> OrderStatus:
        """
        获取订单状态
        
        Args:
            order_id: 订单 ID
            symbol: 交易对
        
        Returns:
            订单状态
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Position:
        """
        获取仓位
        
        Args:
            symbol: 交易对
        
        Returns:
            仓位信息
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> float:
        """
        获取可用余额
        
        Returns:
            可用余额（USDT）
        """
        pass
