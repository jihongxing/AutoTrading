# Core/State 全局状态机 — 设计文档

## 模块结构

```
backend/src/core/state/
├── __init__.py
├── states.py           # 状态定义
├── transitions.py      # 状态转换器
├── machine.py          # 状态机核心
├── claim_processor.py  # Claim 处理器
├── regime.py           # Trade Regime 管理
├── storage.py          # 状态持久化
└── service.py          # 状态机服务
```

## 设计决策

### D-1: 状态分层
```
Layer 1: 系统存在态（由风控裁决）
- SYSTEM_INIT
- RISK_LOCKED
- RECOVERY

Layer 2: 交易许可态（由状态机管理）
- OBSERVING
- ELIGIBLE
- ACTIVE_TRADING
- COOLDOWN
```

### D-2: 状态转换图
```
SYSTEM_INIT
    ↓
OBSERVING ←──────────────┐
    ↓                    │
ELIGIBLE                 │
    ↓                    │
ACTIVE_TRADING           │
    ↓                    │
COOLDOWN ────────────────┘
    
任意状态 → RISK_LOCKED → RECOVERY → OBSERVING
```

### D-3: 风控优先
风控可以从任意状态强制转换到 RISK_LOCKED。

### D-4: 状态转换原子性
使用锁保证状态转换的原子性。

## 接口定义

### StateMachine
```python
class StateMachine:
    @property
    def current_state(self) -> SystemState
    
    async def transition(
        self, target: SystemState, reason: str
    ) -> bool
    
    def can_transition(self, target: SystemState) -> bool
    
    async def force_lock(self, reason: str) -> None
```

### ClaimProcessor
```python
class ClaimProcessor:
    async def process_claim(
        self, claim: Claim
    ) -> ProcessResult:
        """
        处理策略 Claim
        1. 验证 Claim 有效性
        2. 调用风控检查
        3. 决定状态转换
        """
        pass
```

### TradeRegime
```python
class TradeRegime(str, Enum):
    VOLATILITY_EXPANSION = "volatility_expansion"
    RANGE_STRUCTURE_BREAK = "range_structure_break"
    LIQUIDITY_SWEEP = "liquidity_sweep"
    NO_REGIME = "no_regime"
```

### StateMachineService
```python
class StateMachineService:
    async def submit_claim(self, claim: Claim) -> ProcessResult
    async def get_current_state(self) -> SystemState
    async def get_current_regime(self) -> TradeRegime | None
    async def is_trading_allowed(self) -> bool
```

## 状态转换规则表

| 当前状态 | 目标状态 | 条件 |
|----------|----------|------|
| SYSTEM_INIT | OBSERVING | 初始化完成 |
| OBSERVING | ELIGIBLE | Claim + 风控批准 |
| ELIGIBLE | ACTIVE_TRADING | 执行交易 |
| ACTIVE_TRADING | COOLDOWN | 交易完成 |
| COOLDOWN | OBSERVING | 冷却结束 |
| * | RISK_LOCKED | 风控触发 |
| RISK_LOCKED | RECOVERY | 解锁条件满足 |
| RECOVERY | OBSERVING | 恢复完成 |

## 依赖关系
- 依赖: common, data, core/risk
- 被依赖: core/execution, strategy
