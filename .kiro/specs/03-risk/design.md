# Core/Risk 内核级风控 — 设计文档

## 模块结构

```
backend/src/core/risk/
├── __init__.py
├── constants.py      # 风控常量
├── base.py           # 风控基类
├── account_risk.py   # 账户生存性风控
├── execution_risk.py # 执行完整性风控
├── regime_risk.py    # 策略失效风控
├── behavior_risk.py  # 行为风控
├── system_risk.py    # 系统稳定性风控
├── engine.py         # 风控引擎
└── recovery.py       # 恢复管理器
```

## 设计决策

### D-1: 风控状态层级
```
RISK_LOCKED  ← 最高优先级
    ↑
COOLDOWN
    ↑
WARNING
    ↑
NORMAL
```

### D-2: 风控检查流程
```
交易请求 → 风控引擎 → 各风险域检查器 → 聚合结果 → 批准/否决
```

### D-3: 风控否决不可逆
一旦风控否决，当前交易周期内不可重试。

### D-4: 风控阈值分层
- L2 阈值：人工审批修改
- 不允许自学习触碰

## 接口定义

### RiskChecker 基类
```python
class RiskChecker(ABC):
    @abstractmethod
    async def check(self, context: RiskContext) -> RiskCheckResult:
        """执行风控检查"""
        pass
```

### RiskControlEngine
```python
class RiskControlEngine:
    async def check_permission(
        self, context: RiskContext
    ) -> RiskCheckResult:
        """检查是否允许交易"""
        pass
    
    async def force_lock(self, reason: str) -> None:
        """强制锁定系统"""
        pass
    
    async def request_unlock(self) -> bool:
        """请求解锁"""
        pass
```

### RiskContext
```python
class RiskContext(BaseModel):
    equity: float
    drawdown: float
    daily_pnl: float
    consecutive_losses: int
    current_position: float
    recent_trades: list[Trade]
    witness_health: dict[str, WitnessHealth]
```

### RiskCheckResult
```python
class RiskCheckResult(BaseModel):
    approved: bool
    level: RiskLevel
    reason: str | None
    events: list[RiskEvent]
    timestamp: datetime
```

## 风控阈值（L2）

```yaml
account_risk:
  max_drawdown: 0.20
  daily_max_loss: 0.03
  consecutive_loss_cooldown: 3
  weekly_max_loss: 0.10

market_risk:
  volatility_threshold_multiplier: 2.0
  liquidity_threshold: 0.005
  extreme_volatility_threshold: 0.10

position:
  max_single_position: 0.05
  max_total_position: 0.30
  max_leverage: 5

cooldown:
  normal_seconds: 600
  stop_loss_seconds: 1200
  consecutive_loss_seconds: 3600
```

## 依赖关系
- 依赖: common, data
- 被依赖: core/state, core/execution
