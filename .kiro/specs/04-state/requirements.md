# Core/State 全局状态机 — 需求文档

## 模块定位
系统唯一交易入口，管理系统状态转换，决定是否允许交易。

## 宪法级原则
1. 状态机是唯一交易入口
2. 不能绕过状态机直接交易
3. 风控可以强制状态转换
4. 状态转换必须可审计

## 功能需求

### FR-1: 状态定义
- FR-1.1: SYSTEM_INIT — 系统初始化
- FR-1.2: OBSERVING — 观察市场
- FR-1.3: ELIGIBLE — 允许交易
- FR-1.4: ACTIVE_TRADING — 交易中
- FR-1.5: COOLDOWN — 冷却期
- FR-1.6: RISK_LOCKED — 风控锁定
- FR-1.7: RECOVERY — 恢复期

### FR-2: 状态转换规则
- FR-2.1: SYSTEM_INIT → OBSERVING（初始化完成）
- FR-2.2: OBSERVING → ELIGIBLE（策略 Claim + 风控批准）
- FR-2.3: ELIGIBLE → ACTIVE_TRADING（执行交易）
- FR-2.4: ACTIVE_TRADING → COOLDOWN（交易完成）
- FR-2.5: COOLDOWN → OBSERVING（冷却结束）
- FR-2.6: 任意状态 → RISK_LOCKED（风控触发）
- FR-2.7: RISK_LOCKED → RECOVERY（解锁条件满足）
- FR-2.8: RECOVERY → OBSERVING（恢复完成）

### FR-3: 禁止的状态转换
- FR-3.1: OBSERVING → ACTIVE_TRADING（绕过 ELIGIBLE）
- FR-3.2: RISK_LOCKED → ELIGIBLE（绕过 RECOVERY）
- FR-3.3: COOLDOWN → ACTIVE_TRADING（绕过 OBSERVING）

### FR-4: Claim 处理
- FR-4.1: 接收策略 Claim
- FR-4.2: 验证 Claim 有效性
- FR-4.3: 调用风控检查
- FR-4.4: 决定状态转换

### FR-5: Trade Regime 输出
- FR-5.1: 输出当前允许的交易范式
- FR-5.2: 输出风险边界约束
- FR-5.3: 输出推荐持仓时间

### FR-6: 状态查询
- FR-6.1: 获取当前状态
- FR-6.2: 获取状态历史
- FR-6.3: 获取状态持续时间

## 非功能需求

### NFR-1: 响应时间
- 状态切换延迟 < 1 K线周期

### NFR-2: 可靠性
- 状态转换原子性
- 状态持久化

### NFR-3: 可审计
- 所有状态变化记录日志
- 状态转换可回放

## 约束条件
- 状态机不输出买卖方向
- 状态机不输出具体下单参数
- 状态机不做策略优劣判断
