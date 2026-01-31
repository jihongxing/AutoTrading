-- BTC 自动交易系统 - QuestDB 表初始化
-- 执行: curl -G --data-urlencode "query@init_questdb.sql" http://localhost:9000/exec

-- K 线数据表
CREATE TABLE IF NOT EXISTS market_bar (
    ts TIMESTAMP,
    symbol SYMBOL,
    interval SYMBOL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    quote_volume DOUBLE,
    trades LONG
) TIMESTAMP(ts) PARTITION BY DAY WAL;

-- 资金费率表
CREATE TABLE IF NOT EXISTS funding_rate (
    ts TIMESTAMP,
    symbol SYMBOL,
    funding_rate DOUBLE,
    mark_price DOUBLE,
    index_price DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH WAL;

-- 清算数据表
CREATE TABLE IF NOT EXISTS liquidation (
    ts TIMESTAMP,
    symbol SYMBOL,
    side SYMBOL,
    quantity DOUBLE,
    price DOUBLE,
    usd_value DOUBLE
) TIMESTAMP(ts) PARTITION BY DAY WAL;

-- 持仓量表
CREATE TABLE IF NOT EXISTS open_interest (
    ts TIMESTAMP,
    symbol SYMBOL,
    open_interest DOUBLE,
    open_interest_value DOUBLE
) TIMESTAMP(ts) PARTITION BY DAY WAL;

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    ts TIMESTAMP,
    order_id SYMBOL,
    strategy_id SYMBOL,
    symbol SYMBOL,
    side SYMBOL,
    order_type SYMBOL,
    quantity DOUBLE,
    price DOUBLE,
    status SYMBOL,
    executed_qty DOUBLE,
    executed_price DOUBLE,
    commission DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH WAL;

-- 交易记录表
CREATE TABLE IF NOT EXISTS trades (
    ts TIMESTAMP,
    trade_id SYMBOL,
    order_id SYMBOL,
    strategy_id SYMBOL,
    symbol SYMBOL,
    side SYMBOL,
    quantity DOUBLE,
    price DOUBLE,
    commission DOUBLE,
    pnl DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH WAL;

-- 风控事件表
CREATE TABLE IF NOT EXISTS risk_events (
    ts TIMESTAMP,
    event_type SYMBOL,
    severity SYMBOL,
    source SYMBOL,
    message STRING,
    details STRING
) TIMESTAMP(ts) PARTITION BY MONTH WAL;

-- 证人健康度表
CREATE TABLE IF NOT EXISTS witness_health (
    ts TIMESTAMP,
    strategy_id SYMBOL,
    grade SYMBOL,
    success_rate DOUBLE,
    sharpe_ratio DOUBLE,
    max_drawdown DOUBLE,
    stability DOUBLE,
    score DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH WAL;

-- 学习参数表
CREATE TABLE IF NOT EXISTS learning_params (
    ts TIMESTAMP,
    strategy_id SYMBOL,
    param_name SYMBOL,
    param_value DOUBLE,
    previous_value DOUBLE,
    reason STRING
) TIMESTAMP(ts) PARTITION BY MONTH WAL;


-- ========================================
-- 多用户 SaaS 表
-- ========================================

-- 用户收益表
CREATE TABLE IF NOT EXISTS user_profits (
    ts TIMESTAMP,
    user_id SYMBOL,
    trade_id SYMBOL,
    symbol SYMBOL,
    side SYMBOL,
    realized_pnl DOUBLE,
    fee_rate DOUBLE,
    platform_fee DOUBLE,
    net_profit DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH WAL;

-- 用户订单表（带 user_id）
CREATE TABLE IF NOT EXISTS user_orders (
    ts TIMESTAMP,
    user_id SYMBOL,
    order_id SYMBOL,
    strategy_id SYMBOL,
    symbol SYMBOL,
    side SYMBOL,
    order_type SYMBOL,
    quantity DOUBLE,
    price DOUBLE,
    status SYMBOL,
    executed_qty DOUBLE,
    executed_price DOUBLE,
    commission DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH WAL;

-- 用户交易记录表（带 user_id）
CREATE TABLE IF NOT EXISTS user_trades (
    ts TIMESTAMP,
    user_id SYMBOL,
    trade_id SYMBOL,
    order_id SYMBOL,
    strategy_id SYMBOL,
    symbol SYMBOL,
    side SYMBOL,
    quantity DOUBLE,
    price DOUBLE,
    commission DOUBLE,
    pnl DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH WAL;

-- 用户风控事件表
CREATE TABLE IF NOT EXISTS user_risk_events (
    ts TIMESTAMP,
    user_id SYMBOL,
    event_type SYMBOL,
    severity SYMBOL,
    message STRING,
    details STRING
) TIMESTAMP(ts) PARTITION BY MONTH WAL;

-- 用户日收益汇总表
CREATE TABLE IF NOT EXISTS user_daily_summary (
    ts TIMESTAMP,
    user_id SYMBOL,
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    gross_profit DOUBLE,
    gross_loss DOUBLE,
    net_pnl DOUBLE,
    platform_fees DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH WAL;
