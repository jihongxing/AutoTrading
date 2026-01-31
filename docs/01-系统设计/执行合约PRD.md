# BTC 自动交易系统

## 执行合约 PRD（内核级）

---

## 0. 文档定位（必读）

本 PRD 定义 **Execution Contract（执行合约）** 的内核级规范，用于约束 **交易引擎** 在所有策略、风控、状态机交互下的执行行为。执行合约是整个系统的**最后一层防线**，保证执行安全、可审计、可回滚。

> 执行合约 = 系统内核的“防火墙 + 仲裁官”

---

## 1. 设计目标与原则

### 1.1 设计目标

- 确保执行层严格遵守风控与状态机决策
    
- 防止策略、学习模块直接驱动交易
    
- 提供可审计、可回滚的执行记录
    
- 保证系统在极端市场情况下存活
    

### 1.2 核心原则（不可违反）

1. **交易必须获得许可**：任何下单请求必须通过 TradePermission 接口
    
2. **不允许策略直接控制执行**：所有指令由策略裁决层生成的 Claim 驱动
    
3. **强制回滚和冻结机制**：RISK_LOCKED 或异常执行时，立即冻结交易并回滚
    
4. **全程日志化**：每一次下单、修改、撤单都必须可审计
    

---

## 2. 执行层接口定义

### 2.1 ExecuteOrder（核心执行接口）

```text
ExecuteOrder(order) -> ExecutionResult
```

**前置条件**：

- `TradePermission == true`
    
- 当前 GlobalState == ACTIVE_TRADING
    

**输入参数**：

- order_id
    
- symbol
    
- side (BUY/SELL)
    
- quantity
    
- price_type (MARKET/LIMIT)
    
- validity_window
    
- strategy_id
    

**执行逻辑**：

1. 验证策略发言权等级
    
2. 检查风控锁定
    
3. 检查状态机许可
    
4. 执行订单（或模拟执行）
    
5. 记录 ExecutionResult
    
6. 如执行异常触发 RISK_LOCKED
    

---

### 2.2 CancelOrder（撤单接口）

```text
CancelOrder(order_id) -> CancelResult
```

- 可在 ACTIVE_TRADING 或 COOLDOWN 状态下使用
    
- 撤单必须记录原因
    
- 撤单触发异常同样可导致 RISK_LOCKED
    

---

### 2.3 FreezeExecution（冻结接口）

```text
FreezeExecution(reason) -> FreezeResult
```

- 风控触发或状态异常时自动调用
    
- 禁止所有新订单执行
    
- 当前订单执行完成后，标记冻结
    
- 可选人工介入解除
    

---

### 2.4 RollbackExecution（回滚接口）

```text
RollbackExecution(order_ids) -> RollbackResult
```

- 针对策略误操作或执行异常
    
- 回滚应保证订单与系统状态一致
    
- 严格受风控控制，执行前必须验证 TradePermission
    

---

## 3. ExecutionResult 结构

```text
{
    order_id,
    strategy_id,
    status: [FILLED, PARTIALLY_FILLED, REJECTED, CANCELLED],
    executed_quantity,
    executed_price,
    timestamp,
    flags: [RISK_LOCKED_TRIGGERED, COOLDOWN_TRIGGERED]
}
```

- **flags** 用于触发全局状态机和风控
    

---

## 4. 系统不可越权约束

1. 执行层不能：
    
    - 调整策略输出
        
    - 修改策略发言权等级
        
    - 绕过风控或状态机
        
2. 所有异常必须被立即记录
    
3. RISK_LOCKED 必须优先于任何交易执行
    

---

## 5. 最小可执行核心要求（Minimal Kernel 版）

- 接受 Dummy Strategy 信号
    
- 执行模拟交易
    
- 在异常或风控锁定下，立即冻结
    
- 记录日志以便审计和回滚
    

---

## 6. 可审计与追踪机制

每条交易记录必须包括：

- 时间戳
    
- 调用来源（策略ID、合约ID）
    
- 执行结果
    
- 风控标记
    
- 全局状态标记
    

---

## 7. 失败与异常处理

### 7.1 失败触发条件

- 风控锁定
    
- 状态机不允许交易
    
- 执行异常（交易所拒单、网络异常等）
    

### 7.2 异常响应

- 自动 FreezeExecution
    
- 触发 RISK_LOCKED
    
- 写入系统日志
    
- 触发 RECOVERY 状态（如适用）
    

---

## 8. 最终目标

> 执行合约保证：

- **安全**：任何策略错误不会导致损失
    
- **可控**：任何异常可以被立即冻结和回滚
    
- **可审计**：所有执行行为可复现、可追溯
    

一旦执行合约生效：

- 所有策略、学习模块、状态机的输出只能作为输入
    
- **真正的下单权在执行合约手中**
    

---

## 9. 总结（宪法级）

> 执行合约是系统的“最后防线”，  
> 策略是证人，状态机是行政，风控是宪法，  
> 执行合约是仲裁官。
> 
> 任何交易行为，必须通过这道门。