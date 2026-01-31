"""
BTC 自动交易系统 — 枚举定义

所有枚举已冻结，不可随意修改。
"""

from enum import Enum


class SystemState(str, Enum):
    """系统状态（状态机）"""
    SYSTEM_INIT = "system_init"
    OBSERVING = "observing"
    ELIGIBLE = "eligible"
    ACTIVE_TRADING = "active_trading"
    COOLDOWN = "cooldown"
    RISK_LOCKED = "risk_locked"
    RECOVERY = "recovery"


class ClaimType(str, Enum):
    """策略声明类型（白名单）"""
    MARKET_ELIGIBLE = "market_eligible"
    MARKET_NOT_ELIGIBLE = "market_not_eligible"
    REGIME_MATCHED = "regime_matched"
    REGIME_CONFLICT = "regime_conflict"
    EXECUTION_VETO = "execution_veto"


class WitnessTier(str, Enum):
    """证人等级"""
    TIER_1 = "tier_1"  # 核心证人：p < 0.05, 胜率 52-55%
    TIER_2 = "tier_2"  # 辅助证人：p < 0.20, 胜率 51-53%
    TIER_3 = "tier_3"  # 否决证人：仅否决权


class WitnessStatus(str, Enum):
    """证人状态"""
    ACTIVE = "active"      # 正常
    MUTED = "muted"        # 静默
    BANNED = "banned"      # 封禁


class OrderSide(str, Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    """风险等级"""
    NORMAL = "normal"
    WARNING = "warning"
    COOLDOWN = "cooldown"
    RISK_LOCKED = "risk_locked"


class RiskEventType(str, Enum):
    """风险事件类型"""
    DRAWDOWN_EXCEEDED = "drawdown_exceeded"
    DAILY_LOSS_EXCEEDED = "daily_loss_exceeded"
    CONSECUTIVE_LOSS = "consecutive_loss"
    VOLATILITY_SPIKE = "volatility_spike"
    LIQUIDITY_LOW = "liquidity_low"
    EXECUTION_FAILURE = "execution_failure"


class HealthGrade(str, Enum):
    """证人健康度等级"""
    A = "A"  # ≥55%, 权重+5%
    B = "B"  # 52-55%, 保持
    C = "C"  # 30-52%, 权重-5%
    D = "D"  # <30%, Mute


class HypothesisStatus(str, Enum):
    """假设状态（假设工厂）"""
    NEW = "new"              # 新生成
    VALIDATING = "validating" # 验证中
    TIER_1 = "tier_1"        # 核心弱信号（p < 0.05, 胜率 52-55%）
    TIER_2 = "tier_2"        # 辅助弱信号（p < 0.20, 胜率 51-53%）
    TIER_3 = "tier_3"        # 观察级（p < 0.30, 胜率 50-52%）
    FAIL = "fail"            # 无效
    PROMOTED = "promoted"    # 已晋升为证人
    DEPRECATED = "deprecated" # 曾有效但失效


class StrategyStatus(str, Enum):
    """策略生命周期状态"""
    NEW = "new"           # 新发现
    TESTING = "testing"   # 回测验证中
    SHADOW = "shadow"     # 影子运行中
    ACTIVE = "active"     # 正式运行
    DEGRADED = "degraded" # 已降权
    RETIRED = "retired"   # 已废弃
