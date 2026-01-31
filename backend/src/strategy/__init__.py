"""
BTC 自动交易系统 — 策略层

策略层负责：
1. 证人管理（注册、健康度）
2. 信号生成（Claim）
3. 策略编排（聚合、冲突消解）

架构约束：
- 策略只能输出 Claim，不能直接下单
- TIER 3 证人具有一票否决权
"""

from .base import BaseStrategy
from .health import HealthManager, TradeResult
from .orchestrator import (
    AggregatedResult,
    ConflictResolution,
    HighTradingWindow,
    StrategyOrchestrator,
)
from .registry import WitnessRegistry
from .witnesses import (
    LiquiditySweepWitness,
    MacroSentinelWitness,
    MicrostructureWitness,
    RangeBreakWitness,
    RiskSentinelWitness,
    TimeStructureWitness,
    VolatilityAsymmetryWitness,
    VolatilityReleaseWitness,
)

__all__ = [
    # 基类
    "BaseStrategy",
    # 注册表
    "WitnessRegistry",
    # 健康度
    "HealthManager",
    "TradeResult",
    # 编排器
    "StrategyOrchestrator",
    "AggregatedResult",
    "ConflictResolution",
    "HighTradingWindow",
    # TIER 1 证人
    "VolatilityReleaseWitness",
    "RangeBreakWitness",
    # TIER 2 证人
    "TimeStructureWitness",
    "VolatilityAsymmetryWitness",
    "LiquiditySweepWitness",
    "MicrostructureWitness",
    # TIER 3 证人
    "RiskSentinelWitness",
    "MacroSentinelWitness",
]
