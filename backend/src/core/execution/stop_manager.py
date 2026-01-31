"""
BTC 自动交易系统 — 止盈止损管理器

管理止损、止盈设置和触发检测。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.common.logging import get_logger
from src.common.utils import utc_now

logger = get_logger(__name__)


class TriggerType(str, Enum):
    """触发类型"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"


@dataclass
class StopConfig:
    """止损止盈配置"""
    position_id: str
    symbol: str
    side: str  # LONG / SHORT
    entry_price: float
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    trailing_stop_percent: float | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class TriggerEvent:
    """触发事件"""
    position_id: str
    trigger_type: TriggerType
    trigger_price: float
    current_price: float
    timestamp: datetime = field(default_factory=utc_now)


class StopManager:
    """
    止盈止损管理器
    
    管理止损、止盈设置和触发检测。
    """
    
    def __init__(self):
        self._configs: dict[str, StopConfig] = {}
        self._highest_prices: dict[str, float] = {}  # 用于追踪止损
        self._lowest_prices: dict[str, float] = {}
    
    async def set_stop_loss(
        self,
        position_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss_price: float,
    ) -> None:
        """
        设置止损
        
        Args:
            position_id: 仓位 ID
            symbol: 交易对
            side: 方向
            entry_price: 入场价
            stop_loss_price: 止损价
        """
        if position_id in self._configs:
            self._configs[position_id].stop_loss_price = stop_loss_price
        else:
            self._configs[position_id] = StopConfig(
                position_id=position_id,
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
            )
        
        logger.info(f"设置止损: {position_id}, 价格: {stop_loss_price}")
    
    async def set_take_profit(
        self,
        position_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        take_profit_price: float,
    ) -> None:
        """
        设置止盈
        
        Args:
            position_id: 仓位 ID
            symbol: 交易对
            side: 方向
            entry_price: 入场价
            take_profit_price: 止盈价
        """
        if position_id in self._configs:
            self._configs[position_id].take_profit_price = take_profit_price
        else:
            self._configs[position_id] = StopConfig(
                position_id=position_id,
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                take_profit_price=take_profit_price,
            )
        
        logger.info(f"设置止盈: {position_id}, 价格: {take_profit_price}")
    
    async def set_trailing_stop(
        self,
        position_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        trailing_percent: float,
    ) -> None:
        """
        设置追踪止损
        
        Args:
            position_id: 仓位 ID
            symbol: 交易对
            side: 方向
            entry_price: 入场价
            trailing_percent: 追踪百分比
        """
        if position_id in self._configs:
            self._configs[position_id].trailing_stop_percent = trailing_percent
        else:
            self._configs[position_id] = StopConfig(
                position_id=position_id,
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                trailing_stop_percent=trailing_percent,
            )
        
        # 初始化最高/最低价
        if side == "LONG":
            self._highest_prices[position_id] = entry_price
        else:
            self._lowest_prices[position_id] = entry_price
        
        logger.info(f"设置追踪止损: {position_id}, 百分比: {trailing_percent:.2%}")
    
    async def check_triggers(
        self,
        current_prices: dict[str, float],
    ) -> list[TriggerEvent]:
        """
        检查触发
        
        Args:
            current_prices: 当前价格 {symbol: price}
        
        Returns:
            触发事件列表
        """
        events: list[TriggerEvent] = []
        
        for position_id, config in self._configs.items():
            current_price = current_prices.get(config.symbol)
            if current_price is None:
                continue
            
            # 更新最高/最低价
            if config.side == "LONG":
                if position_id in self._highest_prices:
                    self._highest_prices[position_id] = max(
                        self._highest_prices[position_id], current_price
                    )
            else:
                if position_id in self._lowest_prices:
                    self._lowest_prices[position_id] = min(
                        self._lowest_prices[position_id], current_price
                    )
            
            # 检查止损
            if config.stop_loss_price:
                if self._is_stop_loss_triggered(config, current_price):
                    events.append(TriggerEvent(
                        position_id=position_id,
                        trigger_type=TriggerType.STOP_LOSS,
                        trigger_price=config.stop_loss_price,
                        current_price=current_price,
                    ))
            
            # 检查止盈
            if config.take_profit_price:
                if self._is_take_profit_triggered(config, current_price):
                    events.append(TriggerEvent(
                        position_id=position_id,
                        trigger_type=TriggerType.TAKE_PROFIT,
                        trigger_price=config.take_profit_price,
                        current_price=current_price,
                    ))
            
            # 检查追踪止损
            if config.trailing_stop_percent:
                trailing_price = self._get_trailing_stop_price(config)
                if trailing_price and self._is_trailing_triggered(config, current_price, trailing_price):
                    events.append(TriggerEvent(
                        position_id=position_id,
                        trigger_type=TriggerType.TRAILING_STOP,
                        trigger_price=trailing_price,
                        current_price=current_price,
                    ))
        
        return events
    
    def remove_config(self, position_id: str) -> None:
        """移除配置"""
        if position_id in self._configs:
            del self._configs[position_id]
        if position_id in self._highest_prices:
            del self._highest_prices[position_id]
        if position_id in self._lowest_prices:
            del self._lowest_prices[position_id]
    
    def _is_stop_loss_triggered(self, config: StopConfig, current_price: float) -> bool:
        """检查止损是否触发"""
        if config.stop_loss_price is None:
            return False
        
        if config.side == "LONG":
            return current_price <= config.stop_loss_price
        else:
            return current_price >= config.stop_loss_price
    
    def _is_take_profit_triggered(self, config: StopConfig, current_price: float) -> bool:
        """检查止盈是否触发"""
        if config.take_profit_price is None:
            return False
        
        if config.side == "LONG":
            return current_price >= config.take_profit_price
        else:
            return current_price <= config.take_profit_price
    
    def _get_trailing_stop_price(self, config: StopConfig) -> float | None:
        """获取追踪止损价格"""
        if config.trailing_stop_percent is None:
            return None
        
        if config.side == "LONG":
            highest = self._highest_prices.get(config.position_id)
            if highest:
                return highest * (1 - config.trailing_stop_percent)
        else:
            lowest = self._lowest_prices.get(config.position_id)
            if lowest:
                return lowest * (1 + config.trailing_stop_percent)
        
        return None
    
    def _is_trailing_triggered(
        self,
        config: StopConfig,
        current_price: float,
        trailing_price: float,
    ) -> bool:
        """检查追踪止损是否触发"""
        if config.side == "LONG":
            return current_price <= trailing_price
        else:
            return current_price >= trailing_price
