# Common 公共模块 — 需求文档

## 模块定位
系统基础设施层，为所有模块提供统一的类型定义、常量、异常和工具函数。

## 功能需求

### FR-1: 枚举定义
- FR-1.1: 系统状态枚举（SystemState）
- FR-1.2: 策略声明类型枚举（ClaimType）
- FR-1.3: 证人等级枚举（WitnessTier）
- FR-1.4: 订单相关枚举（OrderSide, OrderStatus, OrderType）
- FR-1.5: 风控相关枚举（RiskLevel, RiskEventType）
- FR-1.6: 证人健康度枚举（HealthGrade, WitnessStatus）

### FR-2: 数据模型（Pydantic v2）
- FR-2.1: 策略声明模型（Claim）— 策略唯一合法输出
- FR-2.2: 证人健康度模型（WitnessHealth）
- FR-2.3: 订单模型（Order）
- FR-2.4: 执行结果模型（ExecutionResult）
- FR-2.5: 风控事件模型（RiskEvent, RiskCheckResult）
- FR-2.6: 市场数据模型（MarketBar, FundingRate, Liquidation）

### FR-3: 宪法级常量（L0）
- FR-3.1: 架构约束常量（ArchitectureConstants）
- FR-3.2: 自学习边界常量（LearningBounds）
- FR-3.3: 禁止自学习触碰的参数列表

### FR-4: 异常体系
- FR-4.1: 基础异常（TradingSystemError）
- FR-4.2: 架构违规异常（ArchitectureViolationError）
- FR-4.3: 策略层异常（StrategyError 及子类）
- FR-4.4: 风控层异常（RiskControlError 及子类）
- FR-4.5: 执行层异常（ExecutionError 及子类）
- FR-4.6: 状态机异常（StateMachineError 及子类）
- FR-4.7: 数据层异常（DataError 及子类）

### FR-5: 工具函数
- FR-5.1: UTC 时间工具（utc_now, to_utc, from_utc_ms）
- FR-5.2: 结构化日志工具（JSONFormatter, get_logger）
- FR-5.3: 重试装饰器（retry_with_backoff）
- FR-5.4: 配置加载工具

## 非功能需求

### NFR-1: 不可变性
- 所有 Pydantic 模型使用 `frozen=True`

### NFR-2: 类型安全
- 100% 类型注解覆盖
- mypy strict 模式通过

### NFR-3: 测试覆盖
- 单元测试覆盖率 ≥ 90%

## 约束条件
- Python 3.11+
- Pydantic v2
- 所有时间使用 UTC
