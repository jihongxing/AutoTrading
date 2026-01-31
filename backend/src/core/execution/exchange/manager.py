"""
BTC 自动交易系统 — 交易所管理器

管理主备交易所切换和故障检测。
"""

from src.common.logging import get_logger
from src.common.models import Order

from .base import ExchangeClient, ExchangeOrderResult, Position

logger = get_logger(__name__)


class ExchangeManager:
    """
    交易所管理器
    
    管理主备交易所，支持故障切换。
    """
    
    def __init__(
        self,
        primary: ExchangeClient,
        backup: ExchangeClient | None = None,
    ):
        self.primary = primary
        self.backup = backup
        self._use_backup = False
        self._failure_count = 0
        self._max_failures = 3
    
    @property
    def current_client(self) -> ExchangeClient:
        """当前使用的客户端"""
        if self._use_backup and self.backup:
            return self.backup
        return self.primary
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self.current_client.is_connected
    
    async def connect(self) -> None:
        """连接交易所"""
        await self.primary.connect()
        if self.backup:
            await self.backup.connect()
        logger.info("交易所管理器已连接")
    
    async def disconnect(self) -> None:
        """断开连接"""
        await self.primary.disconnect()
        if self.backup:
            await self.backup.disconnect()
        logger.info("交易所管理器已断开")
    
    async def place_order(self, order: Order) -> ExchangeOrderResult:
        """下单"""
        try:
            result = await self.current_client.place_order(order)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if self._should_switch():
                self._switch_to_backup()
                return await self.current_client.place_order(order)
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """撤单"""
        try:
            result = await self.current_client.cancel_order(order_id, symbol)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if self._should_switch():
                self._switch_to_backup()
                return await self.current_client.cancel_order(order_id, symbol)
            raise
    
    async def get_position(self, symbol: str) -> Position:
        """获取仓位"""
        return await self.current_client.get_position(symbol)
    
    async def get_balance(self) -> float:
        """获取余额"""
        return await self.current_client.get_balance()
    
    def _on_success(self) -> None:
        """成功时重置计数"""
        self._failure_count = 0
    
    def _on_failure(self) -> None:
        """失败时增加计数"""
        self._failure_count += 1
        logger.warning(f"交易所请求失败，计数: {self._failure_count}")
    
    def _should_switch(self) -> bool:
        """是否应该切换"""
        return (
            self._failure_count >= self._max_failures
            and self.backup is not None
            and not self._use_backup
        )
    
    def _switch_to_backup(self) -> None:
        """切换到备用"""
        if self.backup:
            self._use_backup = True
            self._failure_count = 0
            logger.warning("切换到备用交易所")
    
    def switch_to_primary(self) -> None:
        """切换回主交易所"""
        self._use_backup = False
        self._failure_count = 0
        logger.info("切换回主交易所")
