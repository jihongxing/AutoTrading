# Common 公共模块 — 设计文档

## 模块结构

```
backend/src/common/
├── __init__.py       # 统一导出
├── enums.py          # 枚举定义
├── models.py         # Pydantic 数据模型
├── constants.py      # 宪法级常量（L0）
├── exceptions.py     # 异常体系
├── logging.py        # 结构化日志
├── retry.py          # 重试策略
├── config.py         # 配置加载
└── utils.py          # 工具函数
```

## 设计决策

### D-1: 模型不可变性
所有 Pydantic 模型使用 `model_config = {"frozen": True}`，确保数据一旦创建不可修改。

### D-2: 枚举继承 str
所有枚举继承 `str, Enum`，便于 JSON 序列化和日志输出。

### D-3: 异常层级
```
TradingSystemError
├── ArchitectureViolationError  # 宪法级
├── StrategyError
│   ├── InvalidClaimError
│   └── WitnessMutedError
├── RiskControlError
│   ├── RiskVetoError
│   ├── RiskLockedException
│   └── DrawdownExceededError
├── ExecutionError
│   ├── OrderRejectedError
│   └── OrderTimeoutError
├── StateMachineError
│   └── InvalidStateTransitionError
└── DataError
    ├── DataNotFoundError
    └── DataValidationError
```

### D-4: 常量分层
- L0（ArchitectureConstants）：硬编码，永不修改
- LearningBounds：自学习参数边界

## 接口定义

### Claim 模型
```python
class Claim(BaseModel):
    strategy_id: str
    claim_type: ClaimType
    confidence: float  # 0.0 ~ 1.0
    validity_window: int  # 秒
    direction: str | None  # long/short/none
    constraints: dict[str, Any]
    timestamp: datetime
```

### 日志接口
```python
def get_logger(name: str) -> logging.Logger
```

### 重试装饰器
```python
@retry_with_backoff(max_retries=3, exponential=True)
async def some_io_operation(): ...
```

## 依赖关系
- 无外部模块依赖
- 被所有其他模块依赖
