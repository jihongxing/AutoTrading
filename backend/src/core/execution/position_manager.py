"""
BTC 自动交易系统 — 仓位管理器

管理仓位计算、限制检查和同步。
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime

from src.common.logging import get_logger
from src.common.models import Order
from src.common.utils import utc_now
from src.core.risk.constants import RiskThresholds

from .constants import ExecutionConstants
from .exchange import ExchangeManager, Position

logger = get_logger(__name__)


@dataclass
class PositionSnapshot:
    """仓位快照"""
    position: Position
    balance: float
    timestamp: datetime


class PositionManager:
    """
    仓位管理器
    
    管理仓位计算、限制检查和同步。
    """
    
    def __init__(
        self,
        exchange: ExchangeManager,
        max_single_position: float | None = None,
        max_total_position: float | None = None,
    ):
        self.exchange = exchange
        self.max_single_position = max_single_position or RiskThresholds.position.max_single_position
        self.max_total_position = max_total_position or RiskThresholds.position.max_total_position
        
        self._cached_position: Position | None = None
        self._cached_balance: float = 0.0
        self._last_sync: datetime | None = None
        self._lock = asyncio.Lock()
    
    async def get_current_position(self, symbol: str = "BTCUSDT") -> Position:
        """获取当前仓位"""
        async with self._lock:
            # 检查缓存是否过期
            if self._should_sync():
                await self._sync_position(symbol)
            
            return self._cached_position or Position(
                symbol=symbol, side="NONE", quantity=0, entry_price=0
            )
    
    async def get_balance(self) -> float:
        """获取可用余额"""
        async with self._lock:
            if self._should_sync():
                await self._sync_balance()
            return self._cached_balance
    
    async def check_position_limit(self, order: Order) -> tuple[bool, str]:
        """
        检查仓位限制
        
        Args:
            order: 订单
        
        Returns:
            (是否通过, 原因)
        """
        balance = await self.get_balance()
        if balance <= 0:
            return False, "余额不足"
        
        position = await self.get_current_position(order.symbol)
        
        # 计算订单价值占比
        order_value = order.quantity * (order.price or 0)
        if order_value <= 0:
            # 市价单，使用当前仓位价格估算
            order_value = order.quantity * position.entry_price if position.entry_price > 0 else 0
        
        order_ratio = order_value / balance if balance > 0 else 0
        
        # 检查单笔限制
        if order_ratio > self.max_single_position:
            return False, f"单笔仓位 {order_ratio:.2%} 超过限制 {self.max_single_position:.2%}"
        
        # 计算总仓位
        current_value = position.quantity * position.entry_price
        current_ratio = current_value / balance if balance > 0 else 0
        total_ratio = current_ratio + order_ratio
        
        # 检查总仓位限制
        if total_ratio > self.max_total_position:
            return False, f"总仓位 {total_ratio:.2%} 超过限制 {self.max_total_position:.2%}"
        
        return True, "通过"
    
    async def sync_position(self, symbol: str = "BTCUSDT") -> PositionSnapshot:
        """
        同步仓位
        
        Returns:
            仓位快照
        """
        async with self._lock:
            await self._sync_position(symbol)
            await self._sync_balance()
            
            return PositionSnapshot(
                position=self._cached_position or Position(
                    symbol=symbol, side="NONE", quantity=0, entry_price=0
                ),
                balance=self._cached_balance,
                timestamp=utc_now(),
            )
    
    async def _sync_position(self, symbol: str) -> None:
        """内部同步仓位"""
        try:
            self._cached_position = await self.exchange.get_position(symbol)
            self._last_sync = utc_now()
            logger.info(
                f"仓位同步: {symbol}, 方向: {self._cached_position.side}, "
                f"数量: {self._cached_position.quantity}"
            )
        except Exception as e:
            logger.error(f"仓位同步失败: {e}")
    
    async def _sync_balance(self) -> None:
        """内部同步余额"""
        try:
            self._cached_balance = await self.exchange.get_balance()
            logger.info(f"余额同步: {self._cached_balance:.2f} USDT")
        except Exception as e:
            logger.error(f"余额同步失败: {e}")
    
    def _should_sync(self) -> bool:
        """是否需要同步"""
        if self._last_sync is None:
            return True
        
        elapsed = (utc_now() - self._last_sync).total_seconds()
        return elapsed > ExecutionConstants.POSITION_SYNC_INTERVAL
    
    def get_position_ratio(self) -> float:
        """获取当前仓位占比"""
        if not self._cached_position or self._cached_balance <= 0:
            return 0.0
        
        position_value = self._cached_position.quantity * self._cached_position.entry_price
        return position_value / self._cached_balance
    
    def get_all_positions(self) -> list[Position]:
        """获取所有仓位"""
        if self._cached_position and self._cached_position.quantity > 0:
            return [self._cached_position]
        return []
