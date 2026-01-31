# Core/Execution 执行层 — 设计文档

## 模块结构

```
backend/src/core/execution/
├── __init__.py
├── constants.py          # 执行常量
├── engine.py             # 执行引擎
├── order_manager.py      # 订单管理器
├── position_manager.py   # 仓位管理器
├── stop_manager.py       # 止盈止损管理器
├── logger.py             # 执行日志器
└── exchange/
    ├── __init__.py
    ├── base.py           # 交易所基类
    ├── binance.py        # Binance 客户端
    └── manager.py        # 交易所管理器
```

## 设计决策

### D-1: 执行层职责边界
```
✅ 允许做：
- 接收合法交易指令
- 精确执行订单
- 记录执行日志
- 反馈执行结果

❌ 禁止做：
- 判断行情
- 判断策略
- 修改订单参数
- 绕过风控
```

### D-2: 执行流程
```
交易指令 → 权限检查 → 风控检查 → 执行订单 → 记录日志 → 返回结果
```

### D-3: 并发控制
使用 asyncio.Lock 保证订单执行的顺序性。

### D-4: 幂等性
通过 order_id 保证同一订单不会重复执行。

## 接口定义

### ExecutionEngine
```python
class ExecutionEngine:
    async def execute_order(
        self, order: Order
    ) -> ExecutionResult:
        """
        执行订单
        1. 检查权限（TradePermission）
        2. 检查风控
        3. 执行订单
        4. 记录日志
        """
        pass
    
    async def cancel_order(
        self, order_id: str, reason: str
    ) -> CancelResult:
        """撤销订单"""
        pass
    
    async def freeze(self, reason: str) -> None:
        """冻结执行"""
        pass
```

### ExchangeClient
```python
class ExchangeClient(ABC):
    @abstractmethod
    async def place_order(
        self, order: Order
    ) -> ExchangeOrderResult
    
    @abstractmethod
    async def cancel_order(
        self, order_id: str
    ) -> bool
    
    @abstractmethod
    async def get_position(
        self, symbol: str
    ) -> Position
```

### OrderManager
```python
class OrderManager:
    async def submit_order(self, order: Order) -> str
    async def get_order_status(self, order_id: str) -> OrderStatus
    async def cancel_order(self, order_id: str) -> bool
    async def get_pending_orders(self) -> list[Order]
```

### PositionManager
```python
class PositionManager:
    async def get_current_position(self, symbol: str) -> Position
    async def check_position_limit(self, order: Order) -> bool
    async def sync_position(self) -> None
```

### StopManager
```python
class StopManager:
    async def set_stop_loss(
        self, position_id: str, price: float
    ) -> None
    
    async def set_take_profit(
        self, position_id: str, price: float
    ) -> None
    
    async def check_triggers(self) -> list[TriggerEvent]
```

## 执行结果模型

```python
class ExecutionResult(BaseModel):
    order_id: str
    status: OrderStatus
    executed_quantity: float
    executed_price: float
    slippage: float
    commission: float
    timestamp: datetime
    flags: list[str]  # RISK_LOCKED_TRIGGERED, COOLDOWN_TRIGGERED
```

## 依赖关系
- 依赖: common, data, core/risk, core/state
- 被依赖: api
