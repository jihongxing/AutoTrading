# Data 统一数据层 — 设计文档

## 模块结构

```
backend/src/data/
├── __init__.py
├── collector.py      # 数据采集器
├── storage.py        # 数据存储
├── api.py            # 统一数据访问接口
├── replay.py         # 数据回放引擎
├── quality.py        # 数据质量检查
└── schemas.py        # 数据库 Schema
```

## 设计决策

### D-1: 数据分层存储
```
热数据（7天）  → QuestDB 内存表
温数据（90天） → QuestDB 磁盘表
冷数据（永久） → Parquet 文件
```

### D-2: 数据访问权限
| 模块 | 读权限 | 写权限 |
|------|--------|--------|
| 策略层 | ✅ | ❌ |
| 风控层 | ✅ | ✅ 事件 |
| 执行层 | ✅ | ✅ 订单 |
| 自学习层 | ✅ 历史 | ❌ |
| 数据采集 | ❌ | ✅ |

### D-3: 消息主题设计
```
market.btc.tick      # Tick 数据
market.btc.bar       # K 线数据
strategy.signals     # 策略信号
execution.orders     # 订单事件
risk.events          # 风控事件
```

## 接口定义

### DataAPI
```python
class DataAPI:
    async def get_bars(
        self, symbol: str, interval: str,
        start: datetime, end: datetime
    ) -> list[MarketBar]
    
    async def get_funding_rates(
        self, symbol: str,
        start: datetime, end: datetime
    ) -> list[FundingRate]
    
    async def get_liquidations(
        self, symbol: str,
        start: datetime, end: datetime
    ) -> list[Liquidation]
```

### DataReplay
```python
class DataReplay:
    async def replay_market_data(
        self, start: datetime, end: datetime,
        speed: float = 1.0
    ) -> AsyncIterator[MarketBar]
    
    async def replay_signals(
        self, start: datetime, end: datetime
    ) -> AsyncIterator[StrategySignal]
```

### DataCollector
```python
class DataCollector:
    async def collect_bars(self, symbol: str, interval: str)
    async def collect_funding_rates(self, symbol: str)
    async def collect_with_fallback(self, data_type: str)
```

## 数据库 Schema

### market_bar
```sql
CREATE TABLE market_bar (
    ts TIMESTAMP,
    symbol SYMBOL,
    interval SYMBOL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    quote_volume DOUBLE,
    trades INT
) TIMESTAMP(ts) PARTITION BY DAY;
```

### strategy_signal
```sql
CREATE TABLE strategy_signal (
    signal_id STRING,
    strategy_id SYMBOL,
    direction SYMBOL,
    confidence DOUBLE,
    ts TIMESTAMP
) TIMESTAMP(ts) PARTITION BY DAY;
```

### risk_event
```sql
CREATE TABLE risk_event (
    event_id STRING,
    event_type SYMBOL,
    level SYMBOL,
    description STRING,
    ts TIMESTAMP
) TIMESTAMP(ts) PARTITION BY DAY;
```

## 依赖关系
- 依赖: common
- 被依赖: strategy, core/risk, core/execution, learning
