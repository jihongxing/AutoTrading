# 多用户 SaaS 系统设计

## 需求概述

将单用户系统扩展为多用户 SaaS 模式：
- 用户规模：≤100
- 策略共享，账户隔离
- 用户自己提供 Binance API Key
- 收益分成 + 订阅制计费

## 架构设计

### 模块结构

```
src/
├── user/                    # 新增：用户模块
│   ├── __init__.py
│   ├── models.py           # 用户数据模型
│   ├── manager.py          # 用户管理器
│   ├── context.py          # 用户执行上下文
│   └── crypto.py           # API Key 加密
├── billing/                 # 新增：计费模块
│   ├── __init__.py
│   ├── models.py           # 计费数据模型
│   ├── tracker.py          # 收益跟踪
│   └── calculator.py       # 费用计算
├── core/
│   └── execution/
│       └── multi_executor.py  # 新增：多用户执行器
└── api/
    └── routes/
        ├── auth.py         # 新增：认证接口
        ├── user.py         # 新增：用户接口
        └── admin.py        # 新增：管理接口
```

### 核心类设计

#### 1. UserManager

```python
class UserManager:
    """用户管理器"""
    
    async def create_user(self, email: str, password: str) -> User
    async def get_user(self, user_id: str) -> User | None
    async def get_user_by_email(self, email: str) -> User | None
    async def update_user(self, user_id: str, **kwargs) -> bool
    async def list_active_users(self) -> list[User]
    async def suspend_user(self, user_id: str, reason: str) -> bool
    async def activate_user(self, user_id: str) -> bool
    
    # 交易所配置
    async def set_exchange_config(self, user_id: str, config: UserExchangeConfig) -> bool
    async def get_exchange_config(self, user_id: str) -> UserExchangeConfig | None
    async def verify_api_key(self, user_id: str) -> tuple[bool, str]
```

#### 2. UserContext

```python
class UserContext:
    """用户执行上下文 - 封装单用户的完整执行环境"""
    
    def __init__(self, user: User, config: UserExchangeConfig):
        self.user = user
        self.config = config
        self.exchange_client: BinanceClient
        self.risk_state: UserRiskState
        self.position_manager: PositionManager
    
    async def initialize(self) -> bool
    async def execute_signal(self, signal: TradingSignal) -> ExecutionResult
    async def check_risk(self) -> RiskCheckResult
    async def get_balance(self) -> float
    async def get_position(self, symbol: str) -> Position
```

#### 3. MultiUserExecutor

```python
class MultiUserExecutor:
    """多用户并行执行器"""
    
    def __init__(self, user_manager: UserManager):
        self._contexts: dict[str, UserContext] = {}
    
    async def initialize_all(self) -> None
    async def broadcast_signal(self, signal: TradingSignal) -> dict[str, ExecutionResult]
    async def refresh_user(self, user_id: str) -> bool
    async def remove_user(self, user_id: str) -> bool
    
    def get_active_count(self) -> int
    def get_user_status(self, user_id: str) -> dict
```

#### 4. ProfitTracker

```python
class ProfitTracker:
    """收益跟踪器"""
    
    async def record_trade(self, user_id: str, trade: TradeResult) -> None
    async def calculate_daily_profit(self, user_id: str, date: date) -> UserProfit
    async def calculate_period_profit(self, user_id: str, start: datetime, end: datetime) -> UserProfit
    async def calculate_platform_fee(self, user_id: str, gross_profit: float) -> float
    async def get_user_summary(self, user_id: str) -> ProfitSummary
```

### 数据流

```
策略信号产出:
┌──────────────┐
│ Orchestrator │ → TradingSignal
└──────┬───────┘
       ↓
信号分发:
┌──────────────┐
│ SignalRouter │ → 获取活跃用户列表
└──────┬───────┘
       ↓
并行执行:
┌─────────────────────────────────────┐
│         MultiUserExecutor           │
│  ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │Context A│ │Context B│ │Context│ │
│  │ check   │ │ check   │ │ check │ │
│  │ execute │ │ execute │ │execute│ │
│  │ record  │ │ record  │ │record │ │
│  └────┬────┘ └────┬────┘ └───┬───┘ │
└───────┼──────────┼──────────┼──────┘
        ↓          ↓          ↓
    Binance A  Binance B  Binance C
```

### 安全设计

#### API Key 加密

```python
class ApiKeyCrypto:
    """API Key 加密工具"""
    
    def __init__(self, master_key: bytes):
        # AES-256-GCM
        self._cipher = AESGCM(master_key)
    
    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self._cipher.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()
    
    def decrypt(self, encrypted: str) -> str:
        data = base64.b64decode(encrypted)
        nonce, ciphertext = data[:12], data[12:]
        return self._cipher.decrypt(nonce, ciphertext, None).decode()
```

#### 数据隔离

```python
# 所有用户数据查询自动添加 user_id 过滤
class UserDataAccess:
    def __init__(self, user_id: str, storage: QuestDBStorage):
        self.user_id = user_id
        self.storage = storage
    
    async def get_orders(self, **filters) -> list[Order]:
        # 自动添加 user_id 条件
        return await self.storage.query_orders(user_id=self.user_id, **filters)
```

### 配置参数

```yaml
# config/user.yaml
user:
  max_users: 100
  trial_days: 7
  
  # 订阅计划
  plans:
    free:
      fee_rate: 0.30
      max_position_pct: 0.05
    basic:
      fee_rate: 0.20
      max_position_pct: 0.15
      monthly_price: 29
    pro:
      fee_rate: 0.10
      max_position_pct: 0.30
      monthly_price: 99

  # 安全配置
  security:
    api_key_verify_interval: 86400  # 每日验证
    jwt_expire_seconds: 86400
    password_min_length: 8
    login_max_attempts: 5
    login_lockout_seconds: 900
```

## 接口设计

### 认证接口

```
POST /auth/register
  Request: { email, password }
  Response: { user_id, email, status }

POST /auth/login
  Request: { email, password }
  Response: { access_token, refresh_token, expires_in }

POST /auth/refresh
  Request: { refresh_token }
  Response: { access_token, expires_in }
```

### 用户接口

```
GET /users/me
  Response: { user_id, email, status, subscription, ... }

PUT /users/me/exchange
  Request: { api_key, api_secret, testnet, leverage, max_position_pct }
  Response: { success, is_valid }

GET /users/me/positions
  Response: { positions: [...] }

GET /users/me/profit?period=monthly
  Response: { gross_profit, platform_fee, net_profit, ... }
```

### 管理接口

```
GET /admin/users?status=active&page=1
  Response: { users: [...], total, page }

POST /admin/users/{id}/suspend
  Request: { reason }
  Response: { success }

GET /admin/stats
  Response: { total_users, active_users, total_profit, ... }
```

## 测试要点

1. 用户注册/登录流程
2. API Key 加密/解密
3. API Key 验证（mock Binance）
4. 多用户并行执行
5. 用户数据隔离
6. 收益计算准确性
7. 风控状态独立性

## 依赖

- cryptography（AES 加密）
- PyJWT（JWT 认证）
- bcrypt（密码哈希）
- 现有模块：BinanceClient, RiskEngine, ExecutionEngine
