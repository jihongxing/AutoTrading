"""
BTC 自动交易系统 — 优化器模块

包含各类参数优化器：
- 权重优化器
- 仓位优化器
- 止盈止损优化器
- 窗口优化器
"""

from .weight import WeightOptimizer, WeightSuggestion
from .position import PositionOptimizer, PositionSuggestion
from .stop import StopOptimizer, StopSuggestion
from .window import WindowOptimizer, WindowSuggestion

__all__ = [
    "WeightOptimizer",
    "WeightSuggestion",
    "PositionOptimizer",
    "PositionSuggestion",
    "StopOptimizer",
    "StopSuggestion",
    "WindowOptimizer",
    "WindowSuggestion",
]
