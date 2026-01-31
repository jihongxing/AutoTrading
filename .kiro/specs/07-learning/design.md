# Learning 自学习层 — 设计文档

## 模块结构

```
backend/src/learning/
├── __init__.py
├── constants.py          # 学习常量
├── collector.py          # 数据收集器
├── analyzer.py           # 后验分析器
├── statistics.py         # 统计分析器
├── engine.py             # 学习引擎
├── storage.py            # 参数存储
└── optimizers/
    ├── __init__.py
    ├── weight.py         # 权重优化器
    ├── position.py       # 仓位优化器
    ├── stop.py           # 止盈止损优化器
    └── window.py         # 窗口优化器
```

## 设计决策

### D-1: 自学习边界约束
```python
LEARNING_BOUNDS = {
    "witness_weight": (0.1, 0.9),
    "position_multiplier": (0.5, 1.5),
    "default_position_ratio": (0.01, 0.03),
    "stop_loss_adjustment": (-0.005, 0.005),
    "take_profit_adjustment": (-0.005, 0.005),
    "max_daily_weight_change": 0.05,
}
```

### D-2: 禁止触碰的参数
```python
LEARNING_FORBIDDEN = [
    "max_drawdown",
    "daily_max_loss",
    "weekly_max_loss",
    "max_leverage",
    "max_single_position",
    "max_total_position",
]
```

### D-3: 学习数据白名单
- 仅 NORMAL/WARNING 状态下的数据可用于学习
- COOLDOWN/RISK_LOCKED 数据默认不可训练

### D-4: 调整频率
- 证人权重：每日
- 仓位系数：每日
- 默认仓位比例：每周
- 止盈止损：每周

## 接口定义

### LearningDataCollector
```python
class LearningDataCollector:
    async def collect_trade_data(
        self, start: datetime, end: datetime
    ) -> list[TradeData]
    
    async def collect_signal_data(
        self, start: datetime, end: datetime
    ) -> list[SignalData]
```

### PostTradeAnalyzer
```python
class PostTradeAnalyzer:
    def analyze_trade(
        self, trade: TradeData
    ) -> TradeAnalysis
    
    def analyze_witness_performance(
        self, witness_id: str, trades: list[TradeData]
    ) -> WitnessPerformance
```

### WeightOptimizer
```python
class WeightOptimizer:
    def suggest_weight_adjustment(
        self, witness_id: str, performance: WitnessPerformance
    ) -> WeightSuggestion:
        """
        返回权重调整建议
        - 成功率 > 55% → +5%
        - 成功率 52-55% → 保持
        - 成功率 < 50% → -5%
        - 成功率 < 48% → Mute
        """
        pass
```

### LearningEngine
```python
class LearningEngine:
    async def run_daily_learning(self) -> LearningReport
    async def run_weekly_learning(self) -> LearningReport
    async def apply_suggestions(
        self, suggestions: list[Suggestion], approved: bool
    ) -> None
```

### LearningParamStorage
```python
class LearningParamStorage:
    async def save_params(
        self, params: LearningParams
    ) -> None
    
    async def load_params(self) -> LearningParams
    async def rollback(self, version: int) -> None
    async def get_history(self) -> list[LearningParams]
```

## 学习报告模型

```python
class LearningReport(BaseModel):
    period: str  # daily/weekly
    timestamp: datetime
    
    # 统计
    total_trades: int
    win_rate: float
    avg_pnl: float
    max_drawdown: float
    
    # 建议
    weight_suggestions: list[WeightSuggestion]
    position_suggestions: list[PositionSuggestion]
    stop_suggestions: list[StopSuggestion]
    
    # 需要审批的调整
    requires_approval: list[Suggestion]
```

## 依赖关系
- 依赖: common, data, strategy
- 被依赖: api
