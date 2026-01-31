# 多用户 SaaS 系统 - 任务清单

## Phase 1: 用户模块基础 ✅

### Task 1.1: 用户数据模型
- [x] 创建 `src/user/__init__.py`
- [x] 创建 `src/user/models.py`
- [x] 定义 `UserStatus` 枚举
- [x] 定义 `SubscriptionPlan` 枚举
- [x] 定义 `User` 数据类
- [x] 定义 `UserExchangeConfig` 数据类
- [x] 定义 `UserRiskState` 数据类

### Task 1.2: API Key 加密
- [x] 创建 `src/user/crypto.py`
- [x] 实现 `ApiKeyCrypto` 类
- [x] 实现 `encrypt()` 方法（AES-256-GCM）
- [x] 实现 `decrypt()` 方法
- [x] 添加 cryptography 依赖

### Task 1.3: 用户存储
- [x] 创建 `src/user/storage.py`
- [x] 实现用户 CRUD 操作
- [x] 实现交易所配置存储
- [x] 实现风控状态存储

### Task 1.4: 用户管理器
- [x] 创建 `src/user/manager.py`
- [x] 实现 `UserManager` 类
- [x] 实现 `create_user()` 方法
- [x] 实现 `get_user()` / `get_user_by_email()` 方法
- [x] 实现 `update_user()` 方法
- [x] 实现 `list_active_users()` 方法
- [x] 实现 `suspend_user()` / `activate_user()` 方法
- [x] 实现 `set_exchange_config()` 方法
- [x] 实现 `verify_api_key()` 方法

## Phase 2: 用户执行上下文 ✅

### Task 2.1: UserContext
- [x] 创建 `src/user/context.py`
- [x] 实现 `UserContext` 类
- [x] 实现 `initialize()` 方法（创建 BinanceClient）
- [x] 实现 `execute_signal()` 方法
- [x] 实现 `check_risk()` 方法
- [x] 实现 `get_balance()` / `get_position()` 方法
- [x] 实现 `shutdown()` 方法

### Task 2.2: 多用户执行器
- [x] 创建 `src/core/execution/multi_executor.py`
- [x] 实现 `MultiUserExecutor` 类
- [x] 实现 `initialize_all()` 方法
- [x] 实现 `broadcast_signal()` 方法（并行执行）
- [x] 实现 `refresh_user()` 方法
- [x] 实现 `remove_user()` 方法
- [x] 实现异常隔离（单用户失败不影响其他）

### Task 2.3: 信号路由
- [x] 创建 `src/core/execution/signal_router.py`
- [x] 实现 `SignalRouter` 类
- [x] 实现 `route_signal()` 方法
- [x] 实现用户过滤逻辑

## Phase 3: 认证系统 ✅

### Task 3.1: JWT 认证
- [x] 创建 `src/api/auth.py`
- [x] 实现 `create_access_token()` 方法
- [x] 实现 `verify_token()` 方法
- [x] 实现 `get_current_user()` 依赖
- [x] 添加 PyJWT 依赖

### Task 3.2: 密码处理
- [x] 实现 `hash_password()` 方法
- [x] 实现 `verify_password()` 方法
- [x] 添加 bcrypt 依赖

### Task 3.3: 认证 API
- [x] 创建 `src/api/routes/auth.py`
- [x] 实现 `POST /auth/register` 接口
- [x] 实现 `POST /auth/login` 接口
- [x] 实现 `POST /auth/refresh` 接口
- [x] 实现 `POST /auth/logout` 接口

## Phase 4: 用户 API ✅

### Task 4.1: 用户信息接口
- [x] 创建 `src/api/routes/user.py`
- [x] 实现 `GET /users/me` 接口
- [x] 实现 `PUT /users/me` 接口
- [x] 实现 `PUT /users/me/password` 接口

### Task 4.2: 交易所配置接口
- [x] 实现 `GET /users/me/exchange` 接口
- [x] 实现 `PUT /users/me/exchange` 接口
- [x] 实现 `POST /users/me/exchange/verify` 接口
- [x] 实现 `DELETE /users/me/exchange` 接口

### Task 4.3: 交易数据接口
- [x] 实现 `GET /users/me/positions` 接口
- [x] 实现 `GET /users/me/orders` 接口
- [x] 实现 `GET /users/me/trades` 接口
- [x] 实现 `GET /users/me/risk` 接口

## Phase 5: 计费模块 ✅

### Task 5.1: 计费数据模型
- [x] 创建 `src/billing/__init__.py`
- [x] 创建 `src/billing/models.py`
- [x] 定义 `UserProfit` 数据类
- [x] 定义 `ProfitSummary` 数据类
- [x] 定义 `PlanConfig` 数据类

### Task 5.2: 收益跟踪
- [x] 创建 `src/billing/tracker.py`
- [x] 实现 `ProfitTracker` 类
- [x] 实现 `record_trade()` 方法
- [x] 实现 `calculate_daily_profit()` 方法
- [x] 实现 `calculate_period_profit()` 方法

### Task 5.3: 费用计算
- [x] 创建 `src/billing/calculator.py`
- [x] 实现 `FeeCalculator` 类
- [x] 实现 `calculate_platform_fee()` 方法
- [x] 实现 `get_fee_rate()` 方法（根据订阅计划）

### Task 5.4: 收益 API
- [x] 实现 `GET /users/me/profit` 接口（在 admin.py）
- [x] 实现 `GET /users/me/profit/history` 接口（在 admin.py）

## Phase 6: 管理后台 ✅

### Task 6.1: 管理 API
- [x] 创建 `src/api/routes/admin.py`
- [x] 实现 `GET /admin/users` 接口
- [x] 实现 `GET /admin/users/{id}` 接口
- [x] 实现 `POST /admin/users/{id}/suspend` 接口
- [x] 实现 `POST /admin/users/{id}/activate` 接口
- [x] 实现 `GET /admin/stats` 接口
- [x] 实现 `GET /admin/profit` 接口

### Task 6.2: 管理员认证
- [x] 实现管理员角色检查
- [x] 实现 `require_admin` 依赖（CurrentAdmin）

## Phase 7: 配置和数据库 ✅

### Task 7.1: 配置文件
- [x] 创建 `config/user.yaml`
- [x] 配置订阅计划参数
- [x] 配置安全参数

### Task 7.2: 数据库迁移
- [x] 更新 `scripts/init_questdb.sql`
- [x] 添加 user_profits 表
- [x] 添加 user_orders 表
- [x] 添加 user_trades 表
- [x] 添加 user_risk_events 表
- [x] 添加 user_daily_summary 表

## Phase 8: 测试 ✅

### Task 8.1: 单元测试
- [x] 创建 `tests/unit/user/__init__.py`
- [x] 创建 `tests/unit/user/test_models.py`
- [x] 创建 `tests/unit/user/test_crypto.py`
- [x] 创建 `tests/unit/user/test_manager.py`
- [x] 创建 `tests/unit/user/test_context.py`
- [x] 创建 `tests/unit/billing/test_tracker.py`

### Task 8.2: 集成测试
- [x] 创建 `tests/integration/test_multi_user_flow.py`
- [x] 测试用户注册流程
- [x] 测试 API Key 绑定流程
- [x] 测试多用户并行执行
- [x] 测试数据隔离

### Task 8.3: API 测试
- [x] 创建 `tests/api/test_auth.py`
- [x] 创建 `tests/api/test_user.py`
- [x] 创建 `tests/api/test_admin.py`

## 完成状态

所有 8 个 Phase 已完成，478 测试通过。

## 新增文件清单

```
src/user/
├── __init__.py
├── models.py
├── crypto.py
├── storage.py
├── manager.py
└── context.py

src/billing/
├── __init__.py
├── models.py
├── calculator.py
└── tracker.py

src/api/routes/
├── auth.py
├── user.py
└── admin.py

src/core/execution/
├── multi_executor.py
└── signal_router.py

config/
└── user.yaml

tests/unit/user/
├── __init__.py
├── test_models.py
├── test_crypto.py
├── test_manager.py
└── test_context.py

tests/unit/billing/
├── __init__.py
└── test_tracker.py

tests/api/
├── test_auth.py
├── test_user.py
└── test_admin.py

tests/integration/
└── test_multi_user_flow.py
```
