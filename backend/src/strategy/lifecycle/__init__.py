"""
BTC 自动交易系统 — 策略生命周期管理

包含：
- WeightManager: 动态权重管理
- StrategyPoolManager: 统一策略池管理
- ShadowRunner: 影子运行器
- LifecycleStorage: 状态持久化
"""

from .models import (
    HEALTH_FACTOR_MAP,
    ShadowPerformance,
    ShadowTradeRecord,
    StrategyStateRecord,
    WitnessWeight,
)
from .weight import WeightManager
from .manager import StrategyPoolManager
from .shadow import ShadowRunner
from .storage import LifecycleStorage

__all__ = [
    "WitnessWeight",
    "StrategyStateRecord",
    "ShadowTradeRecord",
    "ShadowPerformance",
    "HEALTH_FACTOR_MAP",
    "WeightManager",
    "StrategyPoolManager",
    "ShadowRunner",
    "LifecycleStorage",
]
