"""
BTC 自动交易系统 — 执行层

执行层只执行，不判断。
"""

from .constants import ExecutionConstants
from .engine import ExecutionEngine
from .exchange import BinanceClient, ExchangeClient, ExchangeManager, ExchangeOrderResult, Position
from .logger import ExecutionLogEntry, ExecutionLogger
from .order_manager import OrderManager, TrackedOrder
from .position_manager import PositionManager, PositionSnapshot
from .stop_manager import StopConfig, StopManager, TriggerEvent, TriggerType

__all__ = [
    # Constants
    "ExecutionConstants",
    # Engine
    "ExecutionEngine",
    # Exchange
    "ExchangeClient",
    "ExchangeOrderResult",
    "Position",
    "BinanceClient",
    "ExchangeManager",
    # Order Manager
    "OrderManager",
    "TrackedOrder",
    # Position Manager
    "PositionManager",
    "PositionSnapshot",
    # Stop Manager
    "StopManager",
    "StopConfig",
    "TriggerEvent",
    "TriggerType",
    # Logger
    "ExecutionLogger",
    "ExecutionLogEntry",
]
