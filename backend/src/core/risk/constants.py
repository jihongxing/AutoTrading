"""
BTC 自动交易系统 — 风控常量

L2 层级阈值，修改需要审批。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AccountRiskThresholds:
    """账户风控阈值"""
    max_drawdown: float = 0.20
    daily_max_loss: float = 0.03
    weekly_max_loss: float = 0.10
    consecutive_loss_cooldown: int = 3


@dataclass(frozen=True)
class MarketRiskThresholds:
    """市场风控阈值"""
    volatility_threshold_multiplier: float = 2.0
    liquidity_threshold: float = 0.005
    extreme_volatility_threshold: float = 0.10


@dataclass(frozen=True)
class PositionThresholds:
    """仓位阈值"""
    max_single_position: float = 0.05
    max_total_position: float = 0.30
    max_leverage: int = 5


@dataclass(frozen=True)
class ExecutionThresholds:
    """执行阈值"""
    max_slippage: float = 0.005
    min_fill_rate: float = 0.95
    max_latency_ms: int = 1000


@dataclass(frozen=True)
class CooldownConfig:
    """冷却期配置"""
    normal_seconds: int = 600
    stop_loss_seconds: int = 1200
    consecutive_loss_seconds: int = 3600


@dataclass(frozen=True)
class RecoveryConfig:
    """恢复配置"""
    auto_unlock_hours: int = 24
    degraded_position_ratio: float = 0.5


class RiskThresholds:
    """风控阈值集合"""
    account = AccountRiskThresholds()
    market = MarketRiskThresholds()
    position = PositionThresholds()
    execution = ExecutionThresholds()
    cooldown = CooldownConfig()
    recovery = RecoveryConfig()


# 阈值允许范围（用于配置验证）
THRESHOLD_RANGES = {
    "max_drawdown": (0.05, 0.30),
    "daily_max_loss": (0.01, 0.10),
    "weekly_max_loss": (0.03, 0.20),
    "consecutive_loss_cooldown": (2, 5),
    "max_single_position": (0.01, 0.10),
    "max_total_position": (0.10, 0.50),
    "max_leverage": (1, 10),
    "max_slippage": (0.001, 0.01),
}
