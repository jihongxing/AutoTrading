"""
BTC 自动交易系统 — 执行日志器

记录订单、执行结果和审计追踪。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.enums import OrderStatus
from src.common.logging import get_logger
from src.common.models import ExecutionResult, Order
from src.common.utils import utc_now

logger = get_logger(__name__)


@dataclass
class ExecutionLogEntry:
    """执行日志条目"""
    log_id: str
    order_id: str
    event_type: str  # ORDER_SUBMITTED, ORDER_FILLED, ORDER_CANCELLED, etc.
    status: OrderStatus
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)


class ExecutionLogger:
    """
    执行日志器
    
    记录所有执行相关的日志，支持审计追踪。
    """
    
    def __init__(self):
        self._logs: list[ExecutionLogEntry] = []
        self._order_logs: dict[str, list[ExecutionLogEntry]] = {}
    
    def log_order_submitted(self, order: Order) -> None:
        """记录订单提交"""
        entry = self._create_entry(
            order_id=order.order_id,
            event_type="ORDER_SUBMITTED",
            status=OrderStatus.SUBMITTED,
            details={
                "symbol": order.symbol,
                "side": order.side.value,
                "type": order.order_type.value,
                "quantity": order.quantity,
                "price": order.price,
                "strategy_id": order.strategy_id,
            },
        )
        self._add_entry(entry)
        logger.info(
            f"订单提交: {order.order_id}",
            extra={"order_id": order.order_id, "event": "ORDER_SUBMITTED"},
        )
    
    def log_order_filled(self, order_id: str, result: ExecutionResult) -> None:
        """记录订单成交"""
        entry = self._create_entry(
            order_id=order_id,
            event_type="ORDER_FILLED",
            status=result.status,
            details={
                "executed_quantity": result.executed_quantity,
                "executed_price": result.executed_price,
                "slippage": result.slippage,
                "commission": result.commission,
                "flags": result.flags,
            },
        )
        self._add_entry(entry)
        logger.info(
            f"订单成交: {order_id}, 价格: {result.executed_price}",
            extra={"order_id": order_id, "event": "ORDER_FILLED"},
        )
    
    def log_order_cancelled(self, order_id: str, reason: str) -> None:
        """记录订单撤销"""
        entry = self._create_entry(
            order_id=order_id,
            event_type="ORDER_CANCELLED",
            status=OrderStatus.CANCELLED,
            details={"reason": reason},
        )
        self._add_entry(entry)
        logger.info(
            f"订单撤销: {order_id}, 原因: {reason}",
            extra={"order_id": order_id, "event": "ORDER_CANCELLED"},
        )
    
    def log_order_rejected(self, order_id: str, reason: str) -> None:
        """记录订单拒绝"""
        entry = self._create_entry(
            order_id=order_id,
            event_type="ORDER_REJECTED",
            status=OrderStatus.REJECTED,
            details={"reason": reason},
        )
        self._add_entry(entry)
        logger.warning(
            f"订单拒绝: {order_id}, 原因: {reason}",
            extra={"order_id": order_id, "event": "ORDER_REJECTED"},
        )
    
    def log_execution_error(self, order_id: str, error: str) -> None:
        """记录执行错误"""
        entry = self._create_entry(
            order_id=order_id,
            event_type="EXECUTION_ERROR",
            status=OrderStatus.REJECTED,
            details={"error": error},
        )
        self._add_entry(entry)
        logger.error(
            f"执行错误: {order_id}, 错误: {error}",
            extra={"order_id": order_id, "event": "EXECUTION_ERROR"},
        )
    
    def get_order_history(self, order_id: str) -> list[ExecutionLogEntry]:
        """获取订单历史"""
        return self._order_logs.get(order_id, [])
    
    def get_recent_logs(self, limit: int = 100) -> list[ExecutionLogEntry]:
        """获取最近日志"""
        return self._logs[-limit:]
    
    def _create_entry(
        self,
        order_id: str,
        event_type: str,
        status: OrderStatus,
        details: dict[str, Any],
    ) -> ExecutionLogEntry:
        """创建日志条目"""
        import uuid
        return ExecutionLogEntry(
            log_id=str(uuid.uuid4()),
            order_id=order_id,
            event_type=event_type,
            status=status,
            details=details,
        )
    
    def _add_entry(self, entry: ExecutionLogEntry) -> None:
        """添加日志条目"""
        self._logs.append(entry)
        
        if entry.order_id not in self._order_logs:
            self._order_logs[entry.order_id] = []
        self._order_logs[entry.order_id].append(entry)
