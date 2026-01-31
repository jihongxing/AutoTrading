# API REST 接口 — 设计文档

## 模块结构

```
backend/src/api/
├── __init__.py
├── app.py              # FastAPI 应用
├── dependencies.py     # 依赖注入
├── auth.py             # 认证模块
├── schemas.py          # 响应模型
└── routes/
    ├── __init__.py
    ├── state.py        # 系统状态路由
    ├── strategy.py     # 策略路由
    ├── risk.py         # 风控路由
    ├── execution.py    # 执行路由
    ├── data.py         # 数据路由
    └── learning.py     # 学习路由
```

## 设计决策

### D-1: RESTful 设计
遵循 RESTful 规范，使用标准 HTTP 方法。

### D-2: 认证方式
使用 API Key 认证，敏感操作需要额外权限。

### D-3: 响应格式
统一 JSON 响应格式：
```json
{
  "success": true,
  "data": {...},
  "error": null,
  "timestamp": "2026-01-30T10:00:00Z"
}
```

### D-4: 错误处理
统一错误响应格式：
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "RISK_LOCKED",
    "message": "系统已被风控锁定"
  },
  "timestamp": "2026-01-30T10:00:00Z"
}
```

## API 端点

### 系统状态
```
GET  /api/v1/state              # 获取当前状态
GET  /api/v1/state/history      # 获取状态历史
POST /api/v1/state/force-lock   # 强制锁定（需认证）
```

### 策略/证人
```
GET  /api/v1/witnesses              # 获取所有证人
GET  /api/v1/witnesses/{id}         # 获取证人详情
GET  /api/v1/witnesses/{id}/health  # 获取证人健康度
POST /api/v1/witnesses/{id}/mute    # 静默证人
POST /api/v1/witnesses/{id}/activate # 激活证人
```

### 风控
```
GET  /api/v1/risk/status    # 获取风控状态
GET  /api/v1/risk/events    # 获取风控事件
POST /api/v1/risk/unlock    # 请求解锁（需认证）
```

### 执行
```
GET  /api/v1/orders             # 获取订单列表
GET  /api/v1/orders/{id}        # 获取订单详情
GET  /api/v1/positions          # 获取当前仓位
POST /api/v1/orders/{id}/cancel # 撤销订单
```

### 数据
```
GET /api/v1/market/bars           # 获取 K 线数据
GET /api/v1/market/funding-rates  # 获取资金费率
GET /api/v1/market/liquidations   # 获取清算数据
```

### 学习
```
GET  /api/v1/learning/report      # 获取学习报告
GET  /api/v1/learning/suggestions # 获取优化建议
POST /api/v1/learning/approve     # 审批建议
```

## 响应模型

### StateResponse
```python
class StateResponse(BaseModel):
    current_state: SystemState
    current_regime: TradeRegime | None
    is_trading_allowed: bool
    state_since: datetime
    risk_level: RiskLevel
```

### WitnessResponse
```python
class WitnessResponse(BaseModel):
    witness_id: str
    tier: WitnessTier
    status: WitnessStatus
    health: WitnessHealth
```

### RiskStatusResponse
```python
class RiskStatusResponse(BaseModel):
    level: RiskLevel
    is_locked: bool
    lock_reason: str | None
    recent_events: list[RiskEvent]
```

## 依赖关系
- 依赖: common, data, core/*, strategy, learning
- 被依赖: 无（最外层）
