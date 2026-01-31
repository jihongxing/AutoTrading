"""
BTC 自动交易系统 — 用户数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.common.utils import utc_now


class UserStatus(str, Enum):
    """用户状态"""
    PENDING = "pending"      # 待激活
    ACTIVE = "active"        # 正常
    SUSPENDED = "suspended"  # 暂停
    BANNED = "banned"        # 封禁


class SubscriptionPlan(str, Enum):
    """订阅计划"""
    FREE = "free"            # 免费试用
    BASIC = "basic"          # 基础版
    PRO = "pro"              # 专业版


# 订阅计划配置
PLAN_CONFIG = {
    SubscriptionPlan.FREE: {
        "fee_rate": 0.30,
        "max_position_pct": 0.05,
        "trial_days": 7,
        "monthly_price": 0,
    },
    SubscriptionPlan.BASIC: {
        "fee_rate": 0.20,
        "max_position_pct": 0.15,
        "trial_days": 0,
        "monthly_price": 29,
    },
    SubscriptionPlan.PRO: {
        "fee_rate": 0.10,
        "max_position_pct": 0.30,
        "trial_days": 0,
        "monthly_price": 99,
    },
}


@dataclass
class User:
    """用户"""
    user_id: str
    email: str
    password_hash: str
    status: UserStatus = UserStatus.PENDING
    subscription: SubscriptionPlan = SubscriptionPlan.FREE
    is_admin: bool = False
    trial_ends_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_trial_expired(self) -> bool:
        if self.subscription != SubscriptionPlan.FREE:
            return False
        if self.trial_ends_at is None:
            return False
        return utc_now() > self.trial_ends_at
    
    @property
    def fee_rate(self) -> float:
        return PLAN_CONFIG[self.subscription]["fee_rate"]
    
    @property
    def max_position_pct(self) -> float:
        return PLAN_CONFIG[self.subscription]["max_position_pct"]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "status": self.status.value,
            "subscription": self.subscription.value,
            "is_admin": self.is_admin,
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class UserExchangeConfig:
    """用户交易所配置"""
    user_id: str
    exchange: str = "binance"
    api_key_encrypted: str = ""
    api_secret_encrypted: str = ""
    testnet: bool = False
    leverage: int = 10
    max_position_pct: float = 0.05
    is_valid: bool = False
    last_verified_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    def to_dict(self, include_keys: bool = False) -> dict[str, Any]:
        # 生成脱敏的 API Key
        api_key_masked = ""
        if self.api_key_encrypted:
            from .crypto import decrypt_api_key
            try:
                key = decrypt_api_key(self.api_key_encrypted)
                if key and len(key) > 8:
                    api_key_masked = key[:4] + "****" + key[-4:]
                elif key:
                    api_key_masked = "****"
            except Exception:
                api_key_masked = "****"
        
        result = {
            "user_id": self.user_id,
            "exchange": self.exchange,
            "testnet": self.testnet,
            "leverage": self.leverage,
            "max_position_pct": self.max_position_pct,
            "is_valid": self.is_valid,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "api_key_masked": api_key_masked,
        }
        if include_keys:
            result["has_api_key"] = bool(self.api_key_encrypted)
        return result


@dataclass
class UserRiskState:
    """用户风控状态"""
    user_id: str
    current_drawdown: float = 0.0
    daily_loss: float = 0.0
    weekly_loss: float = 0.0
    consecutive_losses: int = 0
    is_locked: bool = False
    locked_reason: str | None = None
    locked_at: datetime | None = None
    updated_at: datetime = field(default_factory=utc_now)
    
    def lock(self, reason: str) -> None:
        self.is_locked = True
        self.locked_reason = reason
        self.locked_at = utc_now()
        self.updated_at = utc_now()
    
    def unlock(self) -> None:
        self.is_locked = False
        self.locked_reason = None
        self.locked_at = None
        self.updated_at = utc_now()
    
    def record_loss(self, loss: float) -> None:
        self.daily_loss += loss
        self.weekly_loss += loss
        self.consecutive_losses += 1
        self.updated_at = utc_now()
    
    def record_win(self, profit: float) -> None:
        self.consecutive_losses = 0
        self.updated_at = utc_now()
    
    def reset_daily(self) -> None:
        self.daily_loss = 0.0
        self.updated_at = utc_now()
    
    def reset_weekly(self) -> None:
        self.weekly_loss = 0.0
        self.updated_at = utc_now()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "current_drawdown": self.current_drawdown,
            "daily_loss": self.daily_loss,
            "weekly_loss": self.weekly_loss,
            "consecutive_losses": self.consecutive_losses,
            "is_locked": self.is_locked,
            "locked_reason": self.locked_reason,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
        }
