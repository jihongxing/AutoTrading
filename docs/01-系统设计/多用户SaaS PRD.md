# BTC 自动交易系统 — 多用户 SaaS PRD

> **版本**：v1.0  
> **日期**：2026-01-31  
> **状态**：待评审

---

## 一、概述

### 1.1 背景

当前系统为单用户设计，需扩展为多用户 SaaS 模式，支持多个用户使用同一套策略系统进行自动交易。

### 1.2 目标

- 支持 ≤100 个用户同时使用
- 共享策略，隔离账户和资金
- 用户自己提供 Binance API Key
- 支持收益分成 + 订阅制计费

### 1.3 核心原则

1. **策略共享** — 所有用户使用同一套证人策略
2. **资金隔离** — 每个用户的资金完全独立
3. **风控独立** — 每个用户有独立的风控状态
4. **数据隔离** — 用户只能访问自己的数据

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      策略层（共享）                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 证人 1   │  │ 证人 2   │  │ 证人 N   │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       └─────────────┼─────────────┘                     │
│                     ↓                                   │
│              ┌──────────────┐                           │
│              │  策略编排器   │ → 产出统一交易信号         │
│              └──────┬───────┘                           │
└─────────────────────┼───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                   信号分发层（新增）                      │
│              ┌──────────────┐                           │
│              │ SignalRouter │ → 广播信号给所有用户       │
│              └──────┬───────┘                           │
└─────────────────────┼───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                 多用户执行层（新增）                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ UserContext │  │ UserContext │  │ UserContext │     │
│  │   User A    │  │   User B    │  │   User C    │     │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │     │
│  │ │风控状态 │ │  │ │风控状态 │ │  │ │风控状态 │ │     │
│  │ │执行引擎 │ │  │ │执行引擎 │ │  │ │执行引擎 │ │     │
│  │ │Binance  │ │  │ │Binance  │ │  │ │Binance  │ │     │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
└─────────┼────────────────┼────────────────┼─────────────┘
          ↓                ↓                ↓
      Binance A        Binance B        Binance C
      (用户A的Key)     (用户B的Key)     (用户C的Key)
```

### 2.2 模块职责

| 模块 | 职责 | 变更 |
|------|------|------|
| 策略层 | 产出交易信号 | 无变更，保持共享 |
| SignalRouter | 将信号广播给所有用户 | 新增 |
| UserManager | 用户 CRUD、状态管理 | 新增 |
| UserContext | 封装单用户的执行环境 | 新增 |
| MultiUserExecutor | 并行执行多用户交易 | 新增 |
| ProfitTracker | 收益跟踪和计费 | 新增 |

---

## 三、数据模型

### 3.1 用户模型

```python
class UserStatus(str, Enum):
    PENDING = "pending"      # 待激活
    ACTIVE = "active"        # 正常
    SUSPENDED = "suspended"  # 暂停
    BANNED = "banned"        # 封禁

class SubscriptionPlan(str, Enum):
    FREE = "free"            # 免费试用
    BASIC = "basic"          # 基础版
    PRO = "pro"              # 专业版

@dataclass
class User:
    user_id: str             # UUID
    email: str               # 唯一
    password_hash: str       # bcrypt
    status: UserStatus
    subscription: SubscriptionPlan
    trial_ends_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

### 3.2 交易所配置

```python
@dataclass
class UserExchangeConfig:
    user_id: str
    exchange: str            # "binance"
    api_key_encrypted: str   # AES-256 加密
    api_secret_encrypted: str
    testnet: bool            # 是否测试网
    leverage: int            # 杠杆倍数
    max_position_pct: float  # 最大仓位比例
    is_valid: bool           # API Key 是否有效
    last_verified_at: datetime | None
```

### 3.3 用户风控状态

```python
@dataclass
class UserRiskState:
    user_id: str
    current_drawdown: float
    daily_loss: float
    weekly_loss: float
    consecutive_losses: int
    is_locked: bool          # 是否风控锁定
    locked_reason: str | None
    locked_at: datetime | None
```

### 3.4 收益记录

```python
@dataclass
class UserProfit:
    user_id: str
    period_type: str         # "daily" / "weekly" / "monthly"
    period_start: datetime
    period_end: datetime
    starting_balance: float
    ending_balance: float
    gross_profit: float      # 毛利
    platform_fee: float      # 平台分成
    net_profit: float        # 净利
```

---

## 四、核心流程

### 4.1 用户注册流程

```
1. 用户提交 email + password
2. 验证 email 格式和唯一性
3. 创建用户（status=PENDING）
4. 发送验证邮件
5. 用户点击验证链接
6. 更新 status=ACTIVE，开始试用期
```

### 4.2 API Key 绑定流程

```
1. 用户提交 api_key + api_secret
2. 加密存储
3. 调用 Binance API 验证有效性
4. 检查 API 权限（需要：读取 + 交易）
5. 验证通过 → is_valid=true
6. 验证失败 → 返回错误原因
```

### 4.3 交易信号执行流程

```
1. 策略层产出信号 (TradingSignal)
2. SignalRouter 获取所有活跃用户
3. 过滤：
   - status != ACTIVE → 跳过
   - is_valid != true → 跳过
   - is_locked == true → 跳过
4. 并行执行：
   for user in active_users:
       - 获取用户余额
       - 根据用户配置计算仓位
       - 执行用户独立风控检查
       - 下单
       - 记录结果
5. 汇总执行结果
```

### 4.4 收益计算流程

```
每日结算：
1. 获取用户当日所有成交
2. 计算毛利 = Σ(平仓盈亏)
3. 计算平台分成：
   - 盈利时：fee = gross_profit × fee_rate
   - 亏损时：fee = 0
4. 计算净利 = gross_profit - fee
5. 记录到 user_profits 表
```

---

## 五、API 设计

### 5.1 用户接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /auth/register | 用户注册 |
| POST | /auth/login | 用户登录 |
| POST | /auth/logout | 用户登出 |
| GET | /users/me | 获取当前用户信息 |
| PUT | /users/me | 更新用户信息 |
| PUT | /users/me/password | 修改密码 |

### 5.2 交易所配置接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /users/me/exchange | 获取交易所配置 |
| PUT | /users/me/exchange | 更新交易所配置 |
| POST | /users/me/exchange/verify | 验证 API Key |
| DELETE | /users/me/exchange | 删除交易所配置 |

### 5.3 交易数据接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /users/me/positions | 获取当前仓位 |
| GET | /users/me/orders | 获取订单列表 |
| GET | /users/me/trades | 获取成交记录 |
| GET | /users/me/profit | 获取收益统计 |
| GET | /users/me/risk | 获取风控状态 |

### 5.4 管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/users | 用户列表 |
| GET | /admin/users/{id} | 用户详情 |
| POST | /admin/users/{id}/suspend | 暂停用户 |
| POST | /admin/users/{id}/activate | 激活用户 |
| GET | /admin/stats | 平台统计 |
| GET | /admin/profit | 平台收益 |

---

## 六、安全设计

### 6.1 API Key 安全

1. **加密存储**：AES-256-GCM 加密，密钥从环境变量读取
2. **传输安全**：仅 HTTPS，API Key 不在 URL 中传递
3. **权限最小化**：建议用户只开启"读取+交易"权限，禁用"提现"
4. **定期验证**：每日验证 API Key 有效性

### 6.2 用户认证

1. **密码存储**：bcrypt 哈希，cost=12
2. **JWT Token**：有效期 24 小时，支持刷新
3. **登录限制**：5 次失败后锁定 15 分钟

### 6.3 数据隔离

1. **查询过滤**：所有查询自动添加 user_id 条件
2. **API 鉴权**：用户只能访问自己的资源
3. **审计日志**：记录所有敏感操作

---

## 七、计费设计

### 7.1 订阅计划

| 计划 | 月费 | 分成比例 | 功能限制 |
|------|------|----------|----------|
| FREE | 0 | 30% | 试用 7 天，最大仓位 5% |
| BASIC | $29 | 20% | 最大仓位 15% |
| PRO | $99 | 10% | 最大仓位 30%，优先支持 |

### 7.2 分成规则

- 仅对盈利部分收取分成
- 按日结算，月底汇总
- 亏损不收费，不累计抵扣

### 7.3 结算流程

```
每月 1 日：
1. 计算上月总盈利
2. 计算平台分成
3. 生成账单
4. 通知用户
```

---

## 八、数据库变更

### 8.1 新增表

```sql
-- 用户表
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    subscription VARCHAR(20) NOT NULL DEFAULT 'free',
    trial_ends_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- 用户交易所配置
CREATE TABLE user_exchange_configs (
    user_id VARCHAR(36) PRIMARY KEY,
    exchange VARCHAR(20) NOT NULL DEFAULT 'binance',
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    testnet BOOLEAN NOT NULL DEFAULT false,
    leverage INT NOT NULL DEFAULT 10,
    max_position_pct DOUBLE NOT NULL DEFAULT 0.05,
    is_valid BOOLEAN NOT NULL DEFAULT false,
    last_verified_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- 用户风控状态
CREATE TABLE user_risk_states (
    user_id VARCHAR(36) PRIMARY KEY,
    current_drawdown DOUBLE NOT NULL DEFAULT 0,
    daily_loss DOUBLE NOT NULL DEFAULT 0,
    weekly_loss DOUBLE NOT NULL DEFAULT 0,
    consecutive_losses INT NOT NULL DEFAULT 0,
    is_locked BOOLEAN NOT NULL DEFAULT false,
    locked_reason VARCHAR(255),
    locked_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL
);

-- 用户收益记录
CREATE TABLE user_profits (
    ts TIMESTAMP,
    user_id SYMBOL,
    period_type SYMBOL,
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    starting_balance DOUBLE,
    ending_balance DOUBLE,
    gross_profit DOUBLE,
    platform_fee DOUBLE,
    net_profit DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH;
```

### 8.2 现有表变更

```sql
-- 订单表添加 user_id
ALTER TABLE orders ADD COLUMN user_id SYMBOL;

-- 交易表添加 user_id
ALTER TABLE trades ADD COLUMN user_id SYMBOL;

-- 风控事件表添加 user_id
ALTER TABLE risk_events ADD COLUMN user_id SYMBOL;
```

---

## 九、实现计划

| 阶段 | 内容 | 优先级 | 工作量 |
|------|------|--------|--------|
| P0 | 用户模型 + UserManager | 高 | 1 天 |
| P1 | API Key 加密存储 + 验证 | 高 | 1 天 |
| P2 | UserContext + 多用户执行器 | 高 | 2 天 |
| P3 | 用户 API 接口 | 高 | 1 天 |
| P4 | 用户认证（JWT） | 中 | 1 天 |
| P5 | 收益计算 + 计费 | 中 | 2 天 |
| P6 | 管理后台接口 | 低 | 1 天 |

---

## 十、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| API Key 泄露 | 用户资金损失 | 加密存储 + 权限最小化 |
| 单用户执行失败影响其他用户 | 部分用户无法交易 | 隔离执行，异常不传播 |
| 用户 API Key 失效 | 无法交易 | 定期验证 + 通知用户 |
| 高并发执行 | 性能瓶颈 | 并行执行 + 限流 |

---

## 十一、验收标准

1. 用户可注册、登录、绑定 API Key
2. 交易信号可并行分发给所有活跃用户
3. 每个用户有独立的风控状态
4. 用户只能查看自己的数据
5. 收益可正确计算和记录
