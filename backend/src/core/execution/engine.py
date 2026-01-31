"""
BTC 自动交易系统 — 执行引擎

执行层核心，负责精确、可控、可审计地执行订单。
"""

import asyncio
from dataclasses import dataclass
from typing import Any

from src.common.enums import OrderStatus, SystemState
from src.common.exceptions import (
    ArchitectureViolationError,
    ExecutionError,
    OrderRejectedError,
    SlippageExceededError,
)
from src.common.logging import get_logger
from src.common.models import ExecutionResult, Order
from src.common.utils import utc_now
from src.core.risk.base import RiskContext
from src.core.risk.engine import RiskControlEngine
from src.core.state.service import StateMachineService

from .constants import ExecutionConstants
from .exchange import ExchangeManager
from .logger import ExecutionLogger
from .order_manager import OrderManager
from .position_manager import PositionManager

logger = get_logger(__name__)


@dataclass
class HighTradingWindowContext:
    """高交易窗口上下文"""
    is_active: bool = False
    confidence: float = 0.0
    multiplier: float = 1.0  # 仓位放大系数
    supporting_witnesses: list[str] | None = None
    direction: str | None = None


class ExecutionEngine:
    """
    执行引擎
    
    执行层核心，负责精确、可控、可审计地执行订单。
    执行层只执行，不判断。
    """
    
    # 高交易窗口仓位放大系数（PRD 要求 1.5x）
    HIGH_WINDOW_MULTIPLIER = 1.5
    # 高交易窗口置信度阈值
    HIGH_WINDOW_CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(
        self,
        exchange: ExchangeManager,
        state_service: StateMachineService,
        risk_engine: RiskControlEngine | None = None,
    ):
        self.exchange = exchange
        self.state_service = state_service
        self.risk_engine = risk_engine or state_service.risk_engine
        
        self.order_manager = OrderManager(exchange)
        self.position_manager = PositionManager(exchange)
        self.logger = ExecutionLogger()
        
        self._frozen = False
        self._freeze_reason: str | None = None
        self._lock = asyncio.Lock()
        self._executed_orders: set[str] = set()  # 幂等性
        
        # 高交易窗口上下文
        self._high_window_context = HighTradingWindowContext()
    
    @property
    def is_frozen(self) -> bool:
        """是否被冻结"""
        return self._frozen
    
    def set_high_trading_window(
        self,
        is_active: bool,
        confidence: float = 0.0,
        supporting_witnesses: list[str] | None = None,
        direction: str | None = None,
    ) -> None:
        """
        设置高交易窗口状态
        
        由策略编排器调用，执行层根据此状态调整仓位。
        """
        multiplier = 1.0
        if is_active and confidence >= self.HIGH_WINDOW_CONFIDENCE_THRESHOLD:
            multiplier = self.HIGH_WINDOW_MULTIPLIER
        
        self._high_window_context = HighTradingWindowContext(
            is_active=is_active,
            confidence=confidence,
            multiplier=multiplier,
            supporting_witnesses=supporting_witnesses or [],
            direction=direction,
        )
        
        if is_active:
            logger.info(
                f"高交易窗口激活: 置信度={confidence:.2%}, 放大系数={multiplier}x",
                extra={"confidence": confidence, "multiplier": multiplier},
            )
    
    def get_position_multiplier(self) -> float:
        """获取当前仓位放大系数"""
        return self._high_window_context.multiplier
    
    def _apply_high_window_multiplier(self, order: Order) -> Order:
        """
        应用高交易窗口仓位放大系数
        
        注意：只放大数量，不修改原订单对象
        """
        if not self._high_window_context.is_active:
            return order
        
        multiplier = self._high_window_context.multiplier
        if multiplier <= 1.0:
            return order
        
        # 检查方向是否一致
        if self._high_window_context.direction:
            order_direction = "long" if order.side == "BUY" else "short"
            if order_direction != self._high_window_context.direction:
                logger.warning("订单方向与高交易窗口方向不一致，不应用放大系数")
                return order
        
        # 创建新订单，应用放大系数
        adjusted_quantity = order.quantity * multiplier
        
        logger.info(
            f"应用高交易窗口放大系数: {order.quantity} -> {adjusted_quantity} ({multiplier}x)",
            extra={"original": order.quantity, "adjusted": adjusted_quantity},
        )
        
        return Order(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=adjusted_quantity,
            price=order.price,
            strategy_id=order.strategy_id,
            validity_window=order.validity_window,
        )
    
    async def execute_order(self, order: Order) -> ExecutionResult:
        """
        执行订单
        
        Args:
            order: 订单
        
        Returns:
            执行结果
        """
        async with self._lock:
            # 1. 幂等性检查
            if order.order_id in self._executed_orders:
                logger.warning(f"订单已执行: {order.order_id}")
                raise OrderRejectedError(f"订单已执行: {order.order_id}")
            
            # 2. 冻结检查
            if self._frozen:
                self.logger.log_order_rejected(order.order_id, f"执行层已冻结: {self._freeze_reason}")
                raise ExecutionError(f"执行层已冻结: {self._freeze_reason}")
            
            # 3. 状态机检查（不能绕过状态机）
            if not self.state_service.is_trading_allowed():
                self.logger.log_order_rejected(
                    order.order_id,
                    f"状态机不允许交易: {self.state_service.get_current_state().value}"
                )
                raise ArchitectureViolationError(
                    "不能绕过状态机执行交易",
                    {"state": self.state_service.get_current_state().value},
                )
            
            # 4. 应用高交易窗口仓位放大系数
            adjusted_order = self._apply_high_window_multiplier(order)
            
            # 5. 仓位限制检查（使用调整后的订单）
            passed, reason = await self.position_manager.check_position_limit(adjusted_order)
            if not passed:
                self.logger.log_order_rejected(order.order_id, reason)
                raise OrderRejectedError(reason)
            
            # 6. 提交订单
            await self.order_manager.submit_order(adjusted_order)
            self.logger.log_order_submitted(adjusted_order)
            
            try:
                # 7. 执行订单
                exchange_result = await self.exchange.place_order(adjusted_order)
                
                # 8. 计算滑点
                slippage = self._calculate_slippage(adjusted_order, exchange_result.executed_price)
                
                # 9. 滑点检查
                if slippage > ExecutionConstants.slippage.max_allowed:
                    logger.warning(f"滑点过大: {slippage:.4%}")
                
                # 10. 构建执行结果
                flags = []
                if self._high_window_context.is_active:
                    flags.append("HIGH_WINDOW_APPLIED")
                
                result = ExecutionResult(
                    order_id=order.order_id,
                    status=exchange_result.status,
                    executed_quantity=exchange_result.executed_quantity,
                    executed_price=exchange_result.executed_price,
                    slippage=slippage,
                    commission=exchange_result.commission,
                    flags=flags,
                )
                
                # 11. 记录日志
                if exchange_result.status == OrderStatus.FILLED:
                    self.logger.log_order_filled(order.order_id, result)
                    await self.order_manager.mark_completed(order.order_id, OrderStatus.FILLED)
                    self._executed_orders.add(order.order_id)
                
                return result
                
            except Exception as e:
                self.logger.log_execution_error(order.order_id, str(e))
                await self.order_manager.mark_completed(order.order_id, OrderStatus.REJECTED)
                raise ExecutionError(f"订单执行失败: {e}")
    
    async def cancel_order(self, order_id: str, reason: str) -> bool:
        """
        撤销订单
        
        Args:
            order_id: 订单 ID
            reason: 撤销原因
        
        Returns:
            是否成功
        """
        success = await self.order_manager.cancel_order(order_id, reason)
        if success:
            self.logger.log_order_cancelled(order_id, reason)
        return success
    
    async def cancel_all_orders(self, reason: str) -> int:
        """
        撤销所有订单
        
        Returns:
            撤销数量
        """
        count = await self.order_manager.cancel_all_pending(reason)
        logger.info(f"批量撤销 {count} 个订单")
        return count
    
    async def freeze(self, reason: str) -> None:
        """
        冻结执行
        
        Args:
            reason: 冻结原因
        """
        self._frozen = True
        self._freeze_reason = reason
        
        # 撤销所有待处理订单
        await self.cancel_all_orders(f"执行层冻结: {reason}")
        
        logger.warning(f"执行层已冻结: {reason}")
    
    async def unfreeze(self) -> None:
        """解冻执行"""
        self._frozen = False
        self._freeze_reason = None
        logger.info("执行层已解冻")
    
    async def sync_position(self, symbol: str = "BTCUSDT") -> None:
        """同步仓位"""
        await self.position_manager.sync_position(symbol)
    
    def _calculate_slippage(self, order: Order, executed_price: float) -> float:
        """计算滑点"""
        if order.price is None or order.price == 0:
            return 0.0
        
        return abs(executed_price - order.price) / order.price
