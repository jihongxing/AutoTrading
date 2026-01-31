"""
BTC 自动交易系统 — 证人模块

包含所有证人实现：
- TIER 1: 核心证人（波动率释放、区间破坏）
- TIER 2: 辅助证人（时间结构、波动率不对称、流动性收割、微结构）
- TIER 3: 否决证人（风控、宏观）
"""

from .volatility_release import VolatilityReleaseWitness
from .range_break import RangeBreakWitness
from .time_structure import TimeStructureWitness
from .volatility_asymmetry import VolatilityAsymmetryWitness
from .liquidity_sweep import LiquiditySweepWitness
from .microstructure import MicrostructureWitness
from .risk_sentinel import RiskSentinelWitness
from .macro_sentinel import MacroSentinelWitness

__all__ = [
    "VolatilityReleaseWitness",
    "RangeBreakWitness",
    "TimeStructureWitness",
    "VolatilityAsymmetryWitness",
    "LiquiditySweepWitness",
    "MicrostructureWitness",
    "RiskSentinelWitness",
    "MacroSentinelWitness",
]
