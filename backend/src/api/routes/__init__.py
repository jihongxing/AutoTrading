"""
BTC 自动交易系统 — API 路由模块
"""

from .admin import router as admin_router
from .auth import router as auth_router
from .coordinator import router as coordinator_router
from .data import router as data_router
from .discovery import router as discovery_router
from .execution import router as execution_router
from .learning import router as learning_router
from .lifecycle import router as lifecycle_router
from .risk import router as risk_router
from .state import router as state_router
from .strategy import router as strategy_router
from .user import router as user_router

__all__ = [
    "state_router",
    "strategy_router",
    "risk_router",
    "execution_router",
    "data_router",
    "learning_router",
    "discovery_router",
    "lifecycle_router",
    "auth_router",
    "user_router",
    "admin_router",
    "coordinator_router",
]
