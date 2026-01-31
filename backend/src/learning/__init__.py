"""
BTC 自动交易系统 — 自学习层

自学习层负责：
1. 数据收集（交易、信号、市场）
2. 后验分析（成功/失败、证人表现）
3. 参数优化（权重、仓位、止损止盈、窗口）
4. 学习报告生成

架构约束：
- 自学习是顾问，不是执政者
- 不能直接影响实时交易
- 不能触碰 L2 风控阈值
- 所有调整有边界约束
"""

from .analyzer import PostTradeAnalyzer, TradeAnalysis, WitnessPerformance, WindowAnalysis
from .collector import LearningDataCollector, MarketSnapshot, SignalData, TradeData
from .engine import LearningEngine, LearningReport, Suggestion
from .optimizers import (
    PositionOptimizer,
    PositionSuggestion,
    StopOptimizer,
    StopSuggestion,
    WeightOptimizer,
    WeightSuggestion,
    WindowOptimizer,
    WindowSuggestion,
)
from .statistics import (
    DrawdownStatistics,
    PeriodStatistics,
    PnLStatistics,
    StatisticsAnalyzer,
)
from .storage import LearningParamStorage, LearningParams

__all__ = [
    # 数据收集
    "LearningDataCollector",
    "TradeData",
    "SignalData",
    "MarketSnapshot",
    # 分析器
    "PostTradeAnalyzer",
    "TradeAnalysis",
    "WitnessPerformance",
    "WindowAnalysis",
    # 统计
    "StatisticsAnalyzer",
    "PnLStatistics",
    "DrawdownStatistics",
    "PeriodStatistics",
    # 优化器
    "WeightOptimizer",
    "WeightSuggestion",
    "PositionOptimizer",
    "PositionSuggestion",
    "StopOptimizer",
    "StopSuggestion",
    "WindowOptimizer",
    "WindowSuggestion",
    # 引擎
    "LearningEngine",
    "LearningReport",
    "Suggestion",
    # 存储
    "LearningParamStorage",
    "LearningParams",
]
