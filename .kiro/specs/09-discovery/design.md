# Discovery 假设工厂 — 设计文档

## 模块结构

```
backend/src/discovery/
├── __init__.py
├── factory/
│   ├── __init__.py
│   ├── engine.py              # 工厂引擎
│   └── detectors/
│       ├── __init__.py
│       ├── base.py            # 检测器基类
│       ├── volatility.py      # 波动率检测器
│       ├── volume.py          # 成交量检测器
│       ├── funding.py         # 资金费率检测器
│       └── liquidation.py     # 清算检测器
├── pool/
│   ├── __init__.py
│   ├── models.py              # 假设模型
│   └── manager.py             # 候选池管理
├── validator/
│   ├── __init__.py
│   └── engine.py              # 验证引擎
└── promoter/
    ├── __init__.py
    └── generator.py           # 证人生成器
```

## 设计决策

### D-1: 代码复用映射

| 新模块 | 复用现有代码 |
|--------|--------------|
| `factory/engine.py` | `src/data/api.py` (DataAPI) |
| `validator/engine.py` | `src/learning/statistics.py` (StatisticsAnalyzer) |
| `promoter/generator.py` | `src/strategy/base.py`, `src/strategy/registry.py`, `src/strategy/health.py` |
| `pool/models.py` | `src/common/enums.py`, `src/common/models.py` |

### D-2: 假设状态枚举（扩展 common/enums.py）

```python
class HypothesisStatus(str, Enum):
    NEW = "new"
    VALIDATING = "validating"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    FAIL = "fail"
    PROMOTED = "promoted"
    DEPRECATED = "deprecated"
```

### D-3: 验证阈值

```python
VALIDATION_THRESHOLDS = {
    "tier_1": {"p_value": 0.05, "win_rate": 0.52, "cohens_d": 0.3},
    "tier_2": {"p_value": 0.20, "win_rate": 0.51, "cohens_d": 0.2},
    "tier_3": {"p_value": 0.30, "win_rate": 0.50, "cohens_d": 0.1},
}
```

### D-4: 资源限制

```python
POOL_LIMITS = {
    "max_hypotheses": 100,
    "max_daily_generation": 10,
    "validation_parallelism": 5,
    "min_event_samples": 100,
}
```

## 接口定义

### BaseDetector

```python
class BaseDetector(ABC):
    detector_id: str
    detector_name: str
    
    @abstractmethod
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        pass
    
    @abstractmethod
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        pass
```

### HypothesisFactory

```python
class HypothesisFactory:
    def __init__(self, data_api: DataAPI):
        self.data_api = data_api
        self.detectors: list[BaseDetector] = []
    
    def register_detector(self, detector: BaseDetector) -> None: ...
    async def scan_for_anomalies(self, start: datetime, end: datetime) -> list[AnomalyEvent]: ...
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]: ...
```

### HypothesisPoolManager

```python
class HypothesisPoolManager:
    async def add(self, hypothesis: Hypothesis) -> bool: ...
    async def get(self, hypothesis_id: str) -> Hypothesis | None: ...
    async def update_status(self, hypothesis_id: str, status: HypothesisStatus) -> None: ...
    async def get_by_status(self, status: HypothesisStatus) -> list[Hypothesis]: ...
    async def cleanup_old(self, days: int = 30) -> int: ...
```

### HypothesisValidator

```python
class HypothesisValidator:
    def __init__(self, stats: StatisticsAnalyzer):
        self.stats = stats  # 复用 learning/statistics.py
    
    async def validate(self, hypothesis: Hypothesis, trades: list[TradeData]) -> ValidationResult: ...
    def determine_tier(self, result: ValidationResult) -> HypothesisStatus: ...
    def check_correlation(self, hypothesis: Hypothesis, existing_witnesses: list[str]) -> float: ...
```

### WitnessGenerator

```python
class WitnessGenerator:
    def __init__(self, registry: WitnessRegistry, health_manager: HealthManager):
        self.registry = registry  # 复用 strategy/registry.py
        self.health_manager = health_manager  # 复用 strategy/health.py
    
    def generate_witness_class(self, hypothesis: Hypothesis) -> type[BaseStrategy]: ...
    def register_witness(self, witness: BaseStrategy) -> None: ...
```

## 数据模型

### AnomalyEvent

```python
@dataclass
class AnomalyEvent:
    event_id: str
    detector_id: str
    event_type: str
    timestamp: datetime
    severity: float  # 0-1
    features: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Hypothesis

```python
@dataclass
class Hypothesis:
    id: str
    name: str
    status: HypothesisStatus
    source_detector: str
    source_event: str
    event_definition: str  # Python 表达式
    event_params: dict[str, float]
    expected_direction: str  # long / short / breakout
    expected_win_rate: tuple[float, float]
    validation_result: ValidationResult | None = None
    correlation_with_existing: dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    p_value: float
    win_rate: float
    cohens_d: float
    sample_size: int
    is_robust: bool  # ±20% 参数不翻转
    correlation_max: float
```

## 依赖关系

- 依赖: common, data, learning, strategy
- 被依赖: api（后续添加 discovery 路由）
