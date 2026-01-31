"""
用户模型单元测试
"""

from datetime import timedelta

import pytest

from src.common.utils import utc_now
from src.user.models import (
    PLAN_CONFIG,
    SubscriptionPlan,
    User,
    UserExchangeConfig,
    UserRiskState,
    UserStatus,
)


class TestUserStatus:
    """用户状态枚举测试"""
    
    def test_status_values(self):
        assert UserStatus.PENDING.value == "pending"
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.BANNED.value == "banned"


class TestSubscriptionPlan:
    """订阅计划枚举测试"""
    
    def test_plan_values(self):
        assert SubscriptionPlan.FREE.value == "free"
        assert SubscriptionPlan.BASIC.value == "basic"
        assert SubscriptionPlan.PRO.value == "pro"
    
    def test_plan_config(self):
        assert PLAN_CONFIG[SubscriptionPlan.FREE]["fee_rate"] == 0.30
        assert PLAN_CONFIG[SubscriptionPlan.BASIC]["fee_rate"] == 0.20
        assert PLAN_CONFIG[SubscriptionPlan.PRO]["fee_rate"] == 0.10


class TestUser:
    """用户模型测试"""
    
    def test_create_user(self):
        user = User(
            user_id="test-123",
            email="test@example.com",
            password_hash="hashed",
        )
        
        assert user.user_id == "test-123"
        assert user.email == "test@example.com"
        assert user.status == UserStatus.PENDING
        assert user.subscription == SubscriptionPlan.FREE
    
    def test_is_active(self):
        user = User(
            user_id="test-123",
            email="test@example.com",
            password_hash="hashed",
            status=UserStatus.ACTIVE,
        )
        
        assert user.is_active is True
        
        user.status = UserStatus.SUSPENDED
        assert user.is_active is False
    
    def test_is_trial_expired(self):
        # 未过期
        user = User(
            user_id="test-123",
            email="test@example.com",
            password_hash="hashed",
            subscription=SubscriptionPlan.FREE,
            trial_ends_at=utc_now() + timedelta(days=7),
        )
        assert user.is_trial_expired is False
        
        # 已过期
        user.trial_ends_at = utc_now() - timedelta(days=1)
        assert user.is_trial_expired is True
        
        # 非免费用户
        user.subscription = SubscriptionPlan.BASIC
        assert user.is_trial_expired is False
    
    def test_fee_rate(self):
        user = User(
            user_id="test-123",
            email="test@example.com",
            password_hash="hashed",
            subscription=SubscriptionPlan.FREE,
        )
        assert user.fee_rate == 0.30
        
        user.subscription = SubscriptionPlan.PRO
        assert user.fee_rate == 0.10
    
    def test_max_position_pct(self):
        user = User(
            user_id="test-123",
            email="test@example.com",
            password_hash="hashed",
            subscription=SubscriptionPlan.FREE,
        )
        assert user.max_position_pct == 0.05
        
        user.subscription = SubscriptionPlan.PRO
        assert user.max_position_pct == 0.30
    
    def test_to_dict(self):
        user = User(
            user_id="test-123",
            email="test@example.com",
            password_hash="hashed",
        )
        
        data = user.to_dict()
        
        assert data["user_id"] == "test-123"
        assert data["email"] == "test@example.com"
        assert "password_hash" not in data


class TestUserExchangeConfig:
    """交易所配置测试"""
    
    def test_create_config(self):
        config = UserExchangeConfig(
            user_id="test-123",
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
        )
        
        assert config.user_id == "test-123"
        assert config.exchange == "binance"
        assert config.testnet is False
        assert config.leverage == 10
        assert config.is_valid is False
    
    def test_to_dict(self):
        config = UserExchangeConfig(
            user_id="test-123",
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
        )
        
        data = config.to_dict()
        assert "api_key_encrypted" not in data
        assert "api_secret_encrypted" not in data
        
        data_with_keys = config.to_dict(include_keys=True)
        assert data_with_keys["has_api_key"] is True


class TestUserRiskState:
    """风控状态测试"""
    
    def test_create_state(self):
        state = UserRiskState(user_id="test-123")
        
        assert state.user_id == "test-123"
        assert state.current_drawdown == 0.0
        assert state.is_locked is False
    
    def test_lock_unlock(self):
        state = UserRiskState(user_id="test-123")
        
        state.lock("测试锁定")
        assert state.is_locked is True
        assert state.locked_reason == "测试锁定"
        assert state.locked_at is not None
        
        state.unlock()
        assert state.is_locked is False
        assert state.locked_reason is None
    
    def test_record_loss(self):
        state = UserRiskState(user_id="test-123")
        
        state.record_loss(100.0)
        assert state.daily_loss == 100.0
        assert state.weekly_loss == 100.0
        assert state.consecutive_losses == 1
        
        state.record_loss(50.0)
        assert state.daily_loss == 150.0
        assert state.consecutive_losses == 2
    
    def test_record_win(self):
        state = UserRiskState(user_id="test-123")
        state.consecutive_losses = 3
        
        state.record_win(100.0)
        assert state.consecutive_losses == 0
    
    def test_reset(self):
        state = UserRiskState(user_id="test-123")
        state.daily_loss = 100.0
        state.weekly_loss = 500.0
        
        state.reset_daily()
        assert state.daily_loss == 0.0
        assert state.weekly_loss == 500.0
        
        state.reset_weekly()
        assert state.weekly_loss == 0.0
