# 策略生命周期管理 - 设计文档

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    StrategyPoolManager                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │     HypothesisPoolManager (复用+扩展)                │    │
│  │     NEW → TESTING → SHADOW                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                              ↓ 晋升为 TIER_2                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │     WitnessRegistry (复用+扩展)                       │    │
│  │     ACTIVE ←→ DEGRADED → RETIRED                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                              ↑                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │     WeightManager (新增)                             │    │
│  │     effective = base × health × learning            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 数据模型

### 1. StrategyStatus 枚举

位置: `src/common/enums.py`

```python
class StrategyStatus(str, Enum):
    NEW = "new"
    TESTING = "testing"
    SHADOW = "shadow"
    ACTIVE = "active"
    DEGRADED = "degraded"
    RETIRED = "retired"
```

### 2. WitnessWeight 模型

位置: `src/strategy/lifecycle/models.py`

```python
@dataclass
class WitnessWeight:
    """证人权重"""
    strategy_id: str
    base_weight: float = 1.0       # L1 配置
    health_factor: float = 1.0     # 健康度因子
    learning_factor: float = 1.0   # 自学习因子
    updated_at: datetime = field(default_factory=utc_now)
    
    @property
    def effective_weight(self) -> float:
        return self.base_weight * self.health_factor * self.learning_factor

# 健康度映射
HEALTH_FACTOR_MAP = {
    HealthGrade.A: 1.2,
    HealthGrade.B: 1.0,
    HealthGrade.C: 0.7,
    HealthGrade.D: 0.5,
}
```

### 3. 状态记录

```python
@dataclass
class StrategyStateRecord:
    strategy_id: str
    status: StrategyStatus
    previous_status: StrategyStatus | None
    tier: WitnessTier | None
    changed_at: datetime
    reason: str
    changed_by: str  # "system" | "admin"
```

## 组件设计

### 1. WeightManager

位置: `src/strategy/lifecycle/weight.py`

```python
class WeightManager:
    """权重管理器"""
    
    def __init__(
        self,
        health_manager: HealthManager,
        config_path: str = "config/strategy.yaml",
    ):
        self.health_manager = health_manager
        self._weights: dict[str, WitnessWeight] = {}
        self._load_base_weights(config_path)
    
    def get_weight(self, strategy_id: str) -> WitnessWeight:
        """获取权重（自动更新 health_factor）"""
        weight = self._weights.get(strategy_id, WitnessWeight(strategy_id))
        
        # 更新 health_factor
        health = self.health_manager.get_health(strategy_id)
        if health:
            weight.health_factor = HEALTH_FACTOR_MAP.get(health.grade, 1.0)
        
        return weight
    
    def set_base_weight(self, strategy_id: str, base: float) -> None:
        """设置基础权重（L1 配置）"""
        if strategy_id not in self._weights:
            self._weights[strategy_id] = WitnessWeight(strategy_id)
        self._weights[strategy_id].base_weight = max(0.5, min(2.0, base))
    
    def set_learning_factor(self, strategy_id: str, factor: float) -> None:
        """设置学习因子（由 LearningEngine 调用）"""
        if strategy_id not in self._weights:
            self._weights[strategy_id] = WitnessWeight(strategy_id)
        self._weights[strategy_id].learning_factor = max(0.8, min(1.2, factor))
```

### 2. StrategyPoolManager

位置: `src/strategy/lifecycle/manager.py`

```python
class StrategyPoolManager:
    def __init__(
        self,
        hypothesis_pool: HypothesisPoolManager,
        registry: WitnessRegistry,
        health_manager: HealthManager,
        weight_manager: WeightManager,
        validator: HypothesisValidator,
    ):
        self.hypothesis_pool = hypothesis_pool
        self.registry = registry
        self.health_manager = health_manager
        self.weight_manager = weight_manager
        self.validator = validator
        self._shadow_strategies: dict[str, BaseStrategy] = {}
        self._state_history: list[StrategyStateRecord] = []
    
    # 状态查询
    def get_status(self, strategy_id: str) -> StrategyStatus | None: ...
    def get_all_by_status(self, status: StrategyStatus) -> list[str]: ...
    
    # 晋升（默认 TIER_2）
    async def promote(self, strategy_id: str, by: str = "system") -> bool: ...
    
    # 升级 TIER（需人工审批）
    async def upgrade_tier(self, strategy_id: str) -> bool:
        """TIER_2 → TIER_1"""
        witness = self.registry.get_witness(strategy_id)
        if not witness or witness.tier != WitnessTier.TIER_2:
            return False
        
        # 检查条件：运行 30 天，健康度 A
        health = self.health_manager.get_health(strategy_id)
        if health and health.grade == HealthGrade.A:
            witness.tier = WitnessTier.TIER_1
            return True
        return False
    
    # 降级
    async def demote(self, strategy_id: str, by: str = "system") -> bool: ...
    async def retire(self, strategy_id: str, by: str = "system") -> bool: ...
```

### 3. 改造 StrategyOrchestrator

位置: `src/strategy/orchestrator.py`

```python
class StrategyOrchestrator:
    def __init__(
        self,
        registry: WitnessRegistry,
        health_manager: HealthManager,
        weight_manager: WeightManager,  # 新增
    ):
        self.registry = registry
        self.health_manager = health_manager
        self.weight_manager = weight_manager
    
    def _calculate_total_confidence(
        self, dominant: Claim, supporting: list[Claim]
    ) -> float:
        base = dominant.confidence
        
        for claim in supporting:
            # 使用动态权重
            weight = self.weight_manager.get_weight(claim.strategy_id)
            factor = weight.effective_weight * 0.1  # TIER2_BASE_FACTOR
            
            if claim.direction == dominant.direction:
                base += claim.confidence * factor
            elif claim.direction is not None:
                base -= claim.confidence * factor * 0.5
        
        return min(0.95, max(0.0, base))
```

### 4. ShadowRunner

位置: `src/strategy/lifecycle/shadow.py`

```python
class ShadowRunner:
    def __init__(self, pool_manager: StrategyPoolManager):
        self.pool_manager = pool_manager
        self._records: dict[str, list[ShadowTradeRecord]] = {}
    
    async def run_all(self, market_data: list[MarketBar]) -> list[ShadowTradeRecord]:
        """运行所有 SHADOW 策略"""
        results = []
        for strategy_id in self.pool_manager.get_all_by_status(StrategyStatus.SHADOW):
            strategy = self.pool_manager._shadow_strategies.get(strategy_id)
            if strategy:
                claim = strategy.generate_claim(market_data)
                if claim:
                    record = ShadowTradeRecord(
                        strategy_id=strategy_id,
                        claim=claim,
                        timestamp=utc_now(),
                        market_price=market_data[-1].close,
                    )
                    self._records.setdefault(strategy_id, []).append(record)
                    results.append(record)
        return results
```

## 配置文件

位置: `config/strategy.yaml`

```yaml
# 证人权重配置 (L1)
weights:
  volatility_release:
    base_weight: 1.0
  range_break:
    base_weight: 1.0
  time_structure:
    base_weight: 0.8
  volatility_asymmetry:
    base_weight: 0.8
  liquidity_sweep:
    base_weight: 0.9
  microstructure:
    base_weight: 0.7

# 聚合参数
aggregation:
  tier2_base_factor: 0.1  # TIER_2 基础影响因子
  confidence_threshold: 0.6
```

## API 设计

位置: `src/api/routes/lifecycle.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/lifecycle/strategies` | GET | 获取所有策略状态 |
| `/api/v1/lifecycle/strategies/{id}` | GET | 获取单个策略详情 |
| `/api/v1/lifecycle/strategies/{id}/promote` | POST | 手动晋升 |
| `/api/v1/lifecycle/strategies/{id}/demote` | POST | 手动降级 |
| `/api/v1/lifecycle/strategies/{id}/upgrade-tier` | POST | 升级 TIER |
| `/api/v1/weights` | GET | 获取所有权重 |
| `/api/v1/weights/{id}` | GET | 获取单个权重 |
| `/api/v1/weights/{id}` | PUT | 修改基础权重 |

## 文件结构

```
src/strategy/lifecycle/
├── __init__.py
├── models.py       # WitnessWeight, StrategyStateRecord
├── weight.py       # WeightManager
├── manager.py      # StrategyPoolManager
└── shadow.py       # ShadowRunner

config/
└── strategy.yaml   # 权重配置

src/api/routes/
└── lifecycle.py    # API 路由
```

## 复用清单

| 现有模块 | 复用方式 |
|----------|----------|
| `HypothesisPoolManager` | 扩展 SHADOW 状态 |
| `HypothesisValidator` | 直接复用验证逻辑 |
| `WitnessRegistry` | 扩展状态字段 |
| `HealthManager` | 驱动 health_factor |
| `LearningEngine` | 调用 set_learning_factor |
| `StrategyOrchestrator` | 改造聚合逻辑 |
