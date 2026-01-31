# BTC 自动交易系统 — 统一数据层 PRD（可直接交付开发）

> **目标**：构建系统唯一、可信、可回放的数据事实源  
> **关键词**：统一、可审计、低耦合、高性能

---

## 1. 数据层设计目标

1. **所有模块只信任这一层**
    
2. **任何交易都可用数据重放**
    
3. **策略与执行不直接访问交易所原始数据**
    

---

## 2. 技术选型（冻结）

### 2.1 核心数据库

**QuestDB（冻结选型）**

用途：

- Tick
    
- Bar
    
- 聚合指标
    
- 回测数据源
    

---

### 2.2 消息系统

**Kafka（冻结选型）**

用途：

- 行情流
    
- 成交流
    
- 策略信号事件
    

---

## 3. 数据分类与 Schema 设计

---

### 3.1 行情数据（Market Data）

**表：market_tick**

|字段|类型|说明|
|---|---|---|
|ts|timestamp|交易所时间|
|symbol|string|BTCUSDT|
|price|double|成交价|
|volume|double|成交量|
|side|string|buy/sell|

---

### 3.2 K线数据（Bar）

**表：market_bar**

|字段|类型|
|---|---|
|ts|timestamp|
|symbol|string|
|interval|string|
|open|double|
|high|double|
|low|double|
|close|double|
|volume|double|

---

### 3.3 策略信号（非交易）

**表：strategy_signal**

|字段|说明|
|---|---|
|signal_id|唯一ID|
|strategy_id|来源策略|
|direction|long / short|
|confidence|策略置信度|
|ts|生成时间|

---

### 3.4 风控事件

**表：risk_event**

|字段|说明|
|---|---|
|event_id|ID|
|type|volatility_spike / drawdown|
|level|warning / hard_block|
|ts|时间|

---

### 3.5 交易执行记录

**表：execution_order**

|字段|说明|
|---|---|
|order_id|系统ID|
|exchange_order_id|交易所ID|
|side|buy/sell|
|price||
|qty||
|status|submitted / filled / canceled|
|ts||

---

## 4. 数据访问规范（强约束）

- 策略层：**只读**
    
- 风控层：读 + 写事件
    
- 执行层：写订单状态
    
- 自学习层：历史读
    

---

## 5. 数据回放能力（强制要求）

必须支持：

- 指定时间段重放行情
    
- 重放策略信号
    
- 重放交易执行
    

> **这是系统自证能力的核心**

---

## 6. 交付标准（给工程团队）

- QuestDB schema 初始化脚本
    
- Kafka topic 定义
    
- 数据写入接口（REST / gRPC）
    
- 数据一致性校验任务
    

---

# 三、总结一句话（非常重要）

> **你现在设计的不是“能不能赚钱”，而是“有没有资格赚钱”**

当这两份文档冻结之后：

- 所有后续 PRD 都只能是 **插件**
    
- 没有人可以动内核
    
- 策略失败 ≠ 系统失败