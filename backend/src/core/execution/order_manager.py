"""
BTC 自动交易系统 — 订单管理器

管理订单状态跟踪、超时处理和撤销。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.common.enums import OrderStatus
from src.common.logging import get_logger
from src.common.models import Order
from src.common.utils import utc_now

from .constants import ExecutionConstants
from .exchange import ExchangeManager

logger = get_logger(__name__)


@dataclass
class TrackedOrder:
    """跟踪中的订单"""
    order: Order
    submitted_at: datetime = field(default_factory=utc_now)
    last_checked: datetime = field(default_factory=utc_now)
    check_count: int = 0


class OrderManager:
    """
    订单管理器
    
    管理订单状态跟踪、超时处理和撤销。
    """
    
    def __init__(self, exchange: ExchangeManager):
        self.exchange = exchange
        self._pending_orders: dict[str, TrackedOrder] = {}
        self._completed_orders: dict[str, Order] = {}
        self._lock = asyncio.Lock()
    
    @property
    def pending_count(self) -> int:
        """待处理订单数"""
        return len(self._pending_orders)
    
    async def submit_order(self, order: Order) -> str:
        """
        提交订单
        
        Args:
            order: 订单
        
        Returns:
            订单 ID
        """
        async with self._lock:
            # 检查是否超过最大待处理数
            if self.pending_count >= ExecutionConstants.MAX_PENDING_ORDERS:
                raise RuntimeError(f"待处理订单数超过上限: {ExecutionConstants.MAX_PENDING_ORDERS}")
            
            # 检查幂等性
            if order.order_id in self._pending_orders:
                logger.warning(f"订单已存在: {order.order_id}")
                return order.order_id
            
            if order.order_id in self._completed_orders:
                logger.warning(f"订单已完成: {order.order_id}")
                return order.order_id
            
            # 添加到跟踪列表
            self._pending_orders[order.order_id] = TrackedOrder(order=order)
            logger.info(f"订单已提交: {order.order_id}")
            
            return order.order_id
    
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """获取订单状态"""
        if order_id in self._completed_orders:
            return self._completed_orders[order_id].status
        
        if order_id in self._pending_orders:
            tracked = self._pending_orders[order_id]
            status = await self.exchange.current_client.get_order_status(
                order_id, tracked.order.symbol
            )
            tracked.last_checked = utc_now()
            tracked.check_count += 1
            return status
        
        return OrderStatus.PENDING
    
    async def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """
        撤销订单
        
        Args:
            order_id: 订单 ID
            reason: 撤销原因
        
        Returns:
            是否成功
        """
        async with self._lock:
            if order_id not in self._pending_orders:
                logger.warning(f"订单不存在或已完成: {order_id}")
                return False
            
            tracked = self._pending_orders[order_id]
            
            success = await self.exchange.cancel_order(order_id, tracked.order.symbol)
            
            if success:
                tracked.order.status = OrderStatus.CANCELLED
                self._completed_orders[order_id] = tracked.order
                del self._pending_orders[order_id]
                logger.info(f"订单已撤销: {order_id}, 原因: {reason}")
            
            return success
    
    async def cancel_all_pending(self, reason: str = "批量撤销") -> int:
        """
        撤销所有待处理订单
        
        Returns:
            撤销成功的数量
        """
        cancelled = 0
        order_ids = list(self._pending_orders.keys())
        
        for order_id in order_ids:
            if await self.cancel_order(order_id, reason):
                cancelled += 1
        
        return cancelled
    
    async def mark_completed(
        self,
        order_id: str,
        status: OrderStatus,
    ) -> None:
        """标记订单完成"""
        async with self._lock:
            if order_id in self._pending_orders:
                tracked = self._pending_orders[order_id]
                tracked.order.status = status
                self._completed_orders[order_id] = tracked.order
                del self._pending_orders[order_id]
                logger.info(f"订单已完成: {order_id}, 状态: {status.value}")
    
    def get_pending_orders(self) -> list[Order]:
        """获取所有待处理订单"""
        return [t.order for t in self._pending_orders.values()]
    
    def get_all_orders(self) -> list[Order]:
        """获取所有订单（待处理 + 已完成）"""
        orders = [t.order for t in self._pending_orders.values()]
        orders.extend(self._completed_orders.values())
        return orders
    
    def get_order(self, order_id: str) -> Order | None:
        """获取指定订单"""
        if order_id in self._pending_orders:
            return self._pending_orders[order_id].order
        return self._completed_orders.get(order_id)
    
    async def check_timeouts(self) -> list[str]:
        """
        检查超时订单
        
        Returns:
            超时订单 ID 列表
        """
        timeout_ms = ExecutionConstants.timeout.order_confirm_ms
        timeout_delta = timedelta(milliseconds=timeout_ms)
        
        timed_out: list[str] = []
        now = utc_now()
        
        for order_id, tracked in self._pending_orders.items():
            if now - tracked.submitted_at > timeout_delta:
                timed_out.append(order_id)
        
        return timed_out
