# BTC 自动交易系统 — 假设工厂 PRD

> **文档定位**：策略发现引擎设计规范  
> **核心理念**：系统自动发现弱信号，而非依赖人工构思策略  
> **设计原则**：最大化复用现有代码，与当前架构无缝集成

---

## 1️⃣ 核心理念

### 目标

让系统自己提出"策略假设"，形成**自我发现、自我验证、自我优化**的闭环。

### 输入

- 历史市场数据（K 线、成交量、波动率）— 复用 `src/data/`
- 交易所微结构数据（订单簿、资金费率、清算）— 复用 `src/data/`
- 链上数据（大额转账、交易所净流入）— 扩展 `src/data/`

### 输出

- 可验证的策略假设对象
- 通过验证后晋升为证人 — 复用 `src/strategy/base.py`

### 核心原则

1. **非人工依赖** — 不需要策略工程师手动设计
2. **弱信号导向** — 每个假设不必"强信号"，52-55% 胜率即可
3. **异常驱动** — 先检测市场异常，再生成假设（而非随机组合）
4. **可量化验证** — 每个假设必须通过统计检验
5. **最大复用** — 复用现有数据层、统计模块、策略基类

---

## 2️⃣ 模块架构

### 目录结构

```
backend/src/discovery/
├── factory/              # 假设工厂
│   ├── detectors/        # 异常检测器
│   │   ├── base.py       # 检测器基类
│   │   ├── volatility.py # 波动率异常
│   │   ├── volume.py     # 成交量异常
│   │   ├── funding.py    # 资金费率异常
│   │   ├── liquidation.py # 清算异常
│   │   └── __init__.py
│   ├── engine.py         # 工厂引擎
│   └── __init__.py
│
├── pool/                 # 策略候选池
│   ├── models.py         # 假设模型（扩展 common/models.py）
│   ├── manager.py        # 候选池管理
│   └── __init__.py
│
├── validator/            # 统计验证器（复用 learning/statistics.py）
│   ├── engine.py         # 验证引擎
│   └── __init__.py
│
├── promoter/             # 晋升器
│   ├── generator.py      # 假设 → 证人（复用 strategy/base.py）
│   └── __init__.py
│
└── __init__.py
```

### 模块职责与复用关系

| 模块 | 职责 | 复用现有代码 |
|------|------|--------------|
| **factory/detectors** | 检测市场异常事件 | `src/data/api.py` 获取数据 |
| **pool** | 管理假设生命周期 | `src/common/enums.py` 状态枚举 |
| **validator** | 统计检验和回测 | `src/learning/statistics.py` 全部复用 |
| **promoter** | 假设转为证人 | `src/strategy/base.py`, `src/strategy/registry.py` |

---

## 3️⃣ 代码复用详细映射

### 3.1 数据层复用（无需新建）

假设工厂直接使用 `src/data/api.py` 的 `DataAPI`：

```python
# discovery/factory/engine.py
from src.data.api import DataAPI, DataAccessRole
from src.data.storage import QuestDBStorage

class HypothesisFactory:
    def __init__(self, storage: QuestDBStorage):
        # 复用现有数据接口，使用 LEARNING 角色（只读）
        self.data_api = DataAPI(storage, DataAccessRole.LEARNING)
    
    async def get_market_data(self, start: datetime, end: datetime) -> list[MarketBar]:
        # 直接调用现有方法
        return await self.data_api.get_bars("BTCUSDT", "1m", start, end)
    
    async def get_funding_data(self, start: datetime, end: datetime) -> list[FundingRate]:
        return await self.data_api.get_funding_rates("BTCUSDT", start, end)
    
    async def get_liquidation_data(self, start: datetime, end: datetime) -> list[Liquidation]:
        return await self.data_api.get_liquidations("BTCUSDT", start, end)
```

**复用的现有模型**（`src/common/models.py`）：
- `MarketBar` — K 线数据
- `FundingRate` — 资金费率
- `Liquidation` — 清算数据

### 3.2 统计验证复用（无需新建）

假设验证直接使用 `src/learning/statistics.py`：

```python
# discovery/validator/engine.py
from src.learning.statistics import StatisticsAnalyzer, PnLStatistics

class HypothesisValidator:
    def __init__(self):
        # 复用现有统计分析器
        self.stats = StatisticsAnalyzer()
    
    def validate_hypothesis(self, hypothesis: Hypothesis, trades: list[TradeData]) -> ValidationResult:
        # 复用现有统计方法
        pnl_stats = self.stats.calculate_pnl_statistics(trades)
        sharpe = self.stats.calculate_sharpe_ratio(trades)
        drawdown = self.stats.calculate_drawdown_statistics(trades)
        
        # 判定 TIER
        tier = self._determine_tier(pnl_stats.win_rate, sharpe)
        return ValidationResult(tier=tier, stats=pnl_stats)
```

**复用的现有类**（`src/learning/statistics.py`）：
- `StatisticsAnalyzer.calculate_pnl_statistics()` — 胜率、盈亏
- `StatisticsAnalyzer.calculate_sharpe_ratio()` — 夏普比率
- `StatisticsAnalyzer.calculate_drawdown_statistics()` — 回撤

### 3.3 证人生成复用（继承现有基类）

晋升器生成的证人继承 `src/strategy/base.py`：

```python
# discovery/promoter/generator.py
from src.strategy.base import BaseStrategy
from src.strategy.registry import WitnessRegistry
from src.strategy.health import HealthManager
from src.common.enums import ClaimType, WitnessTier
from src.common.models import Claim, MarketBar

class WitnessGenerator:
    def __init__(self, registry: WitnessRegistry, health_manager: HealthManager):
        # 复用现有注册表和健康度管理器
        self.registry = registry
        self.health_manager = health_manager
    
    def generate_and_register(self, hypothesis: Hypothesis) -> BaseStrategy:
        """从假设生成证人并注册"""
        
        # 动态创建证人类，继承现有基类
        witness_class = self._create_witness_class(hypothesis)
        witness = witness_class()
        
        # 复用现有注册流程
        self.registry.register(witness)
        self.health_manager.initialize_health(witness)
        
        return witness
    
    def _create_witness_class(self, hypothesis: Hypothesis) -> type[BaseStrategy]:
        """动态创建证人类"""
        
        tier = self._map_tier(hypothesis.status)
        event_checker = self._compile_event_definition(hypothesis.event_definition)
        
        class GeneratedWitness(BaseStrategy):
            def __init__(self):
                super().__init__(
                    strategy_id=f"hyp_{hypothesis.id}",
                    tier=tier,
                    validity_window=60,
                )
                self._hypothesis = hypothesis
                self._event_checker = event_checker
            
            def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
                # 检查事件条件
                if self._event_checker(market_data):
                    return self.create_claim(
                        claim_type=ClaimType.MARKET_ELIGIBLE,
                        confidence=0.6,
                        direction=self._hypothesis.expected_direction,
                    )
                return None
        
        return GeneratedWitness
```

**复用的现有类**：
- `BaseStrategy` — 证人基类，继承其架构约束
- `WitnessRegistry` — 证人注册表
- `HealthManager` — 健康度管理
- `Claim` — 策略声明模型
- `WitnessTier` — 证人等级枚举

### 3.4 枚举扩展（扩展现有文件）

在 `src/common/enums.py` 中添加假设状态：

```python
# 添加到 src/common/enums.py

class HypothesisStatus(str, Enum):
    """假设状态"""
    NEW = "new"              # 新生成
    VALIDATING = "validating" # 验证中
    TIER_1 = "tier_1"        # 核心弱信号
    TIER_2 = "tier_2"        # 辅助弱信号
    TIER_3 = "tier_3"        # 观察级
    FAIL = "fail"            # 无效
    PROMOTED = "promoted"    # 已晋升为证人
    DEPRECATED = "deprecated" # 曾有效但失效
```

### 3.5 复用总结

| 新模块 | 复用现有代码 | 新增代码量 |
|--------|--------------|------------|
| `factory/detectors/` | `data/api.py`, `common/models.py` | 中（检测逻辑） |
| `factory/engine.py` | `data/api.py` | 小（调度逻辑） |
| `pool/` | `common/enums.py` | 小（状态管理） |
| `validator/` | `learning/statistics.py` 全部 | 极小（包装层） |
| `promoter/` | `strategy/base.py`, `strategy/registry.py`, `strategy/health.py` | 小（生成逻辑） |

**预估新增代码量**：约 800-1000 行（不含测试）
**复用代码量**：约 2000+ 行

---

## 4️⃣ 数据模型

### 异常事件

```python
@dataclass
class AnomalyEvent:
    """异常事件"""
    event_id: str
    detector_id: str           # 检测器 ID
    event_type: str            # volatility_spike / volume_surge / ...
    timestamp: datetime
    severity: float            # 0-1，异常强度
    features: dict[str, float] # 相关特征值
    metadata: dict[str, Any]
```

### 假设模型

```python
@dataclass
class Hypothesis:
    """策略假设"""
    id: str
    name: str
    status: HypothesisStatus   # NEW / VALIDATING / TIER_1 / TIER_2 / TIER_3 / FAIL
    
    # 来源
    source_detector: str       # 来源检测器
    source_event: str          # 触发事件 ID
    
    # 事件定义（机械化、可执行）
    event_definition: str      # Python 表达式
    event_params: dict[str, float]  # 参数
    
    # 预期效应
    expected_direction: str    # long / short
    expected_win_rate: tuple[float, float]  # (min, max)，如 (0.52, 0.55)
    
    # 验证结果
    validation_result: ValidationResult | None
    
    # 相关性
    correlation_with_existing: dict[str, float]  # 与现有证人的相关性
    
    # 元数据
    created_at: datetime
    updated_at: datetime
```

### 假设状态

```python
class HypothesisStatus(str, Enum):
    NEW = "new"              # 新生成
    VALIDATING = "validating" # 验证中
    TIER_1 = "tier_1"        # 核心弱信号（p < 0.05, 胜率 52-55%）
    TIER_2 = "tier_2"        # 辅助弱信号（p < 0.20, 胜率 51-53%）
    TIER_3 = "tier_3"        # 观察级（p < 0.30, 胜率 50-52%）
    FAIL = "fail"            # 无效
    PROMOTED = "promoted"    # 已晋升为证人
    DEPRECATED = "deprecated" # 曾有效但失效
```

---

## 5️⃣ 检测器设计

### 基类接口

```python
class BaseDetector(ABC):
    """异常检测器基类"""
    
    detector_id: str
    detector_name: str
    
    @abstractmethod
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """检测异常事件"""
        pass
    
    @abstractmethod
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """从异常事件生成假设"""
        pass
```

### 内置检测器

| 检测器 | 检测目标 | 生成假设示例 |
|--------|----------|--------------|
| **VolatilityDetector** | 波动率压缩/释放 | 波动率压缩后突破方向交易 |
| **VolumeDetector** | 成交量异常放大 | 放量突破后跟随趋势 |
| **OrderbookDetector** | 订单簿失衡 | 买卖深度比极端时反向交易 |
| **FundingDetector** | 资金费率极端 | 资金费率 > P95 时做空 |
| **LiquidationDetector** | 清算密度异常 | 清算潮后价格反转 |

### 检测器示例：波动率检测器

```python
class VolatilityDetector(BaseDetector):
    """波动率异常检测器"""
    
    detector_id = "volatility"
    detector_name = "波动率检测器"
    
    # 参数
    compression_threshold: float = 0.5   # 压缩阈值（相对历史）
    release_threshold: float = 2.0       # 释放阈值
    lookback_period: int = 20            # 回看周期
    
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        events = []
        
        # 计算 ATR
        atr = self._calculate_atr(data, self.lookback_period)
        avg_atr = statistics.mean(atr[-100:])
        current_atr = atr[-1]
        
        # 检测压缩
        if current_atr < avg_atr * self.compression_threshold:
            events.append(AnomalyEvent(
                event_id=f"vol_compress_{data[-1].ts}",
                detector_id=self.detector_id,
                event_type="volatility_compression",
                timestamp=from_utc_ms(data[-1].ts),
                severity=(avg_atr - current_atr) / avg_atr,
                features={"atr": current_atr, "avg_atr": avg_atr},
            ))
        
        # 检测释放
        if current_atr > avg_atr * self.release_threshold:
            events.append(AnomalyEvent(
                event_id=f"vol_release_{data[-1].ts}",
                detector_id=self.detector_id,
                event_type="volatility_release",
                timestamp=from_utc_ms(data[-1].ts),
                severity=(current_atr - avg_atr) / avg_atr,
                features={"atr": current_atr, "avg_atr": avg_atr},
            ))
        
        return events
    
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        hypotheses = []
        
        for event in events:
            if event.event_type == "volatility_compression":
                # 假设：压缩后突破方向交易
                hypotheses.append(Hypothesis(
                    id=f"hyp_{event.event_id}",
                    name="波动率压缩后突破",
                    status=HypothesisStatus.NEW,
                    source_detector=self.detector_id,
                    source_event=event.event_id,
                    event_definition="atr < avg_atr * 0.5 AND breakout",
                    event_params={"compression_ratio": 0.5},
                    expected_direction="breakout",  # 跟随突破方向
                    expected_win_rate=(0.52, 0.55),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ))
        
        return hypotheses
```

---

## 6️⃣ 验证流程

### 验证标准（基于弱信号哲学）

| 等级 | p-value | 胜率 | 效应量 | 结果 |
|------|---------|------|--------|------|
| TIER_1 | < 0.05 | 52-55% | Cohen's d > 0.3 | 核心证人 |
| TIER_2 | < 0.20 | 51-53% | Cohen's d > 0.2 | 辅助证人 |
| TIER_3 | < 0.30 | 50-52% | Cohen's d > 0.1 | 观察期 |
| FAIL | ≥ 0.30 | < 50% | - | 归档 |

### 验证检查清单

1. **事件定义检查**
   - [ ] 完全机械化（无主观判断）
   - [ ] 参数鲁棒性（±20% 不翻转）

2. **统计检验**
   - [ ] 方向偏移检验（p-value）
   - [ ] 胜率检验
   - [ ] 效应量检验（Cohen's d）

3. **反事实检验**
   - [ ] 随机对照组
   - [ ] 真事件 vs 伪事件显著差异

4. **相关性检验**
   - [ ] 与现有证人相关性 < 0.7

---

## 7️⃣ 晋升流程

### 假设 → 证人

```python
class WitnessGenerator:
    """证人生成器"""
    
    def generate_witness(self, hypothesis: Hypothesis) -> type[BaseStrategy]:
        """从假设生成证人类"""
        
        # 确定证人等级
        tier = self._determine_tier(hypothesis.status)
        
        # 动态生成证人类
        class GeneratedWitness(BaseStrategy):
            def __init__(self):
                super().__init__(
                    strategy_id=f"witness_{hypothesis.id}",
                    tier=tier,
                    validity_window=60,
                )
                self.hypothesis = hypothesis
            
            def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
                # 检查事件条件
                if self._check_event(market_data):
                    return self.create_claim(
                        claim_type=ClaimType.MARKET_ELIGIBLE,
                        confidence=0.6,
                        direction=self.hypothesis.expected_direction,
                    )
                return None
            
            def _check_event(self, data: list[MarketBar]) -> bool:
                # 执行假设的事件定义
                # ...
                pass
        
        return GeneratedWitness
```

### 晋升后流程

1. 生成证人类
2. 注册到 `WitnessRegistry`
3. 进入观察期（纸上交易）
4. 观察期通过后启用实盘

---

## 8️⃣ 与现有系统集成

### 集成架构

```
┌─────────────────────────────────────────────────────────────┐
│                      假设工厂模块                            │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ 数据扫描 │ → │ 异常检测 │ → │ 假设生成 │ → │ 统计验证 │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │     策略候选池        │
              │  TIER_1 / TIER_2 / TIER_3  │
              └───────────┬───────────┘
                          │ 晋升
                          ▼
              ┌───────────────────────┐
              │   证人注册表          │
              │  WitnessRegistry      │
              └───────────┬───────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      现有内核                               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ 策略编排 │ → │ 状态机   │ → │ 风控引擎 │ → │ 执行引擎 │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │     自学习模块        │
              │  LearningEngine       │
              └───────────┬───────────┘
                          │ 反馈
                          ▼
              ┌───────────────────────┐
              │   假设工厂优化        │
              │  调整检测器参数       │
              └───────────────────────┘
```

### 复用现有模块

| 假设工厂模块 | 复用现有代码 |
|--------------|--------------|
| scanner | `src/data/storage.py`, `src/data/api.py` |
| validator/statistical | `src/learning/statistics.py` |
| promoter | `src/strategy/base.py`, `src/strategy/registry.py` |

---

## 9️⃣ 运行调度

### 调度频率

| 任务 | 频率 | 说明 |
|------|------|------|
| 异常检测 | 每小时 | 扫描最近数据 |
| 假设生成 | 每日 | 汇总异常事件 |
| 统计验证 | 每周 | 批量验证候选池 |
| 晋升检查 | 每周 | TIER_1/2 假设晋升 |
| 反馈优化 | 每月 | 调整检测器参数 |

### 资源限制

- 候选池最大容量：100 个假设
- 每日最大生成：10 个假设
- 验证并行度：5 个假设

---

## 🔟 实现优先级

| 优先级 | 模块 | 工作量 | 依赖 |
|--------|------|--------|------|
| P0 | `pool/hypothesis.py` | 小 | 无 |
| P0 | `pool/manager.py` | 小 | hypothesis.py |
| P0 | `factory/detectors/base.py` | 小 | 无 |
| P0 | `factory/detectors/volatility.py` | 中 | base.py |
| P1 | `validator/statistical.py` | 小 | 复用 learning |
| P1 | `validator/engine.py` | 中 | statistical.py |
| P1 | `promoter/witness_generator.py` | 中 | strategy/base.py |
| P2 | 更多检测器 | 中 | base.py |
| P2 | 自学习反馈 | 中 | learning |

---

## 1️⃣1️⃣ 成功标准

1. **自动发现** — 系统每周能生成 5-10 个新假设
2. **有效筛选** — 假设通过率 10-20%（TIER_1 + TIER_2）
3. **闭环运转** — 从检测到晋升全自动，无需人工干预
4. **持续优化** — 检测器参数根据反馈自动调整

---

**这不是一个策略系统，而是一个策略发现引擎。**
