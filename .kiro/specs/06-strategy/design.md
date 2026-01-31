# Strategy 策略层 — 设计文档

## 模块结构

```
backend/src/strategy/
├── __init__.py
├── base.py              # 策略基类
├── registry.py          # 证人注册表
├── health.py            # 健康度管理
├── orchestrator.py      # 策略编排器
└── witnesses/
    ├── __init__.py
    ├── volatility_release.py   # TIER 1: 波动率释放
    ├── range_break.py          # TIER 1: 区间破坏
    ├── time_structure.py       # TIER 2: 时间结构
    ├── volatility_asymmetry.py # TIER 2: 波动率不对称
    ├── liquidity_sweep.py      # TIER 2: 流动性收割
    ├── microstructure.py       # TIER 2: 微结构异常
    ├── risk_sentinel.py        # TIER 3: 风控证人
    └── macro_sentinel.py       # TIER 3: 宏观证人
```

## 设计决策

### D-1: 证人分级
```
TIER 1（核心证人）：
- 高发言权
- 可声明 MARKET_ELIGIBLE
- 可成为 DOMINANT
- 目标胜率：52-55%

TIER 2（辅助证人）：
- 低发言权
- 不可单独触发交易
- 仅支持或削弱 TIER 1
- 目标胜率：51-53%

TIER 3（否决证人）：
- 一票否决权
- 可输出 EXECUTION_VETO
- 不可推动交易
```

### D-2: Claim 类型白名单
```python
class ClaimType(str, Enum):
    MARKET_ELIGIBLE = "market_eligible"
    MARKET_NOT_ELIGIBLE = "market_not_eligible"
    REGIME_MATCHED = "regime_matched"
    REGIME_CONFLICT = "regime_conflict"
    EXECUTION_VETO = "execution_veto"
```

### D-3: 策略输出约束
策略只能输出 Claim，不能：
- 直接下单
- 感知账户余额
- 计算最终仓位

### D-4: 冲突消解规则
- 两个 TIER 1 证人范式互斥 → REGIME_UNCLEAR，不交易
- TIER 3 否决 → 立即停止

## 接口定义

### BaseStrategy
```python
class BaseStrategy(ABC):
    strategy_id: str
    tier: WitnessTier
    
    @abstractmethod
    def generate_claim(
        self, market_data: list[MarketBar]
    ) -> Claim | None:
        """生成策略声明（唯一合法输出）"""
        pass
    
    # 禁止的方法（架构约束）
    def place_order(self, *args, **kwargs) -> None:
        raise ArchitectureViolationError(...)
```

### WitnessRegistry
```python
class WitnessRegistry:
    def register(self, witness: BaseStrategy) -> None
    def unregister(self, strategy_id: str) -> None
    def get_witness(self, strategy_id: str) -> BaseStrategy
    def get_all_witnesses(self) -> list[BaseStrategy]
    def get_by_tier(self, tier: WitnessTier) -> list[BaseStrategy]
```

### HealthManager
```python
class HealthManager:
    def update_health(
        self, strategy_id: str, trade_result: TradeResult
    ) -> WitnessHealth
    
    def get_health(self, strategy_id: str) -> WitnessHealth
    def check_auto_mute(self, strategy_id: str) -> bool
```

### StrategyOrchestrator
```python
class StrategyOrchestrator:
    async def run_witnesses(
        self, market_data: list[MarketBar]
    ) -> list[Claim]
    
    async def aggregate_claims(
        self, claims: list[Claim]
    ) -> AggregatedResult
    
    async def check_high_trading_window(
        self, claims: list[Claim]
    ) -> HighTradingWindow
```

## 证人健康度等级

| 等级 | 成功率 | 样本量 | 动作 |
|------|--------|--------|------|
| A | ≥55% | ≥50 | 权重 +5% |
| B | 52-55% | ≥50 | 保持 |
| C | 30-52% | ≥50 | 权重 -5% |
| D | <30% | ≥50 | 自动 Mute |

## 依赖关系
- 依赖: common, data
- 被依赖: core/state, learning
