"""
BTC 自动交易系统 — 执行层常量
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential: bool = True


@dataclass(frozen=True)
class TimeoutConfig:
    """超时配置"""
    order_submit_ms: int = 5000
    order_confirm_ms: int = 30000
    cancel_ms: int = 10000


@dataclass(frozen=True)
class SlippageConfig:
    """滑点配置"""
    max_allowed: float = 0.005
    warning_threshold: float = 0.003


class ExecutionConstants:
    """执行层常量"""
    retry = RetryConfig()
    timeout = TimeoutConfig()
    slippage = SlippageConfig()
    
    # 最大待处理订单数
    MAX_PENDING_ORDERS: int = 5
    
    # 仓位同步间隔（秒）
    POSITION_SYNC_INTERVAL: int = 60
    
    # API 限流（每分钟）
    API_RATE_LIMIT: int = 1200
