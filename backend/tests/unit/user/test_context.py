"""
用户执行上下文单元测试
"""

import pytest

from src.user.context import TradingSignal, UserContext, UserExecutionResult
from src.user.models import User, UserExchangeConfig, UserRiskState, UserStatus


class TestTradingSignal:
    """交易信号测试"""
    
    def test_create_signal(self):
        signal = TradingSignal(
            signal_id="sig-001",
            symbol="BTCUSDT",
            direction="long",
            confidence=0.8,
            position_pct=0.02,
            stop_loss_pct=0.01,
            take_profit_pct=0.03,
        )
        
        assert signal.signal_id == "sig-001"
        assert signal.symbol == "BTCUSDT"
        assert signal.direction == "long"


class TestUserExecutionResult:
    """执行结果测试"""
    
    def test_success_result(self):
        result = UserExecutionResult(
            user_id="user-001",
            signal_id="sig-001",
            success=True,
            order_id="order-123",
        )
        
        assert result.success is True
        assert result.order_id == "order-123"
        assert result.error is None
    
    def test_failure_result(self):
        result = UserExecutionResult(
            user_id="user-001",
            signal_id="sig-001",
            success=False,
            error="余额不足",
        )
        
        assert result.success is False
        assert result.error == "余额不足"


class TestUserContext:
    """用户上下文测试"""
    
    @pytest.fixture
    def user(self):
        return User(
            user_id="test-user",
            email="test@example.com",
            password_hash="hashed",
            status=UserStatus.ACTIVE,
        )
    
    @pytest.fixture
    def exchange_config(self):
        return UserExchangeConfig(
            user_id="test-user",
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            testnet=True,
        )
    
    @pytest.fixture
    def risk_state(self):
        return UserRiskState(user_id="test-user")
    
    def test_create_context(self, user, exchange_config, risk_state):
        context = UserContext(
            user=user,
            config=exchange_config,
            risk_state=risk_state,
        )
        
        assert context.user_id == "test-user"
        assert context.is_initialized is False
    
    def test_is_tradeable(self, user, exchange_config, risk_state):
        context = UserContext(
            user=user,
            config=exchange_config,
            risk_state=risk_state,
        )
        
        # 未初始化
        assert context.is_tradeable is False
        
        # 模拟初始化
        context._initialized = True
        exchange_config.is_valid = True
        assert context.is_tradeable is True
        
        # 风控锁定
        risk_state.lock("测试")
        assert context.is_tradeable is False
    
    @pytest.mark.asyncio
    async def test_check_risk(self, user, exchange_config, risk_state):
        context = UserContext(
            user=user,
            config=exchange_config,
            risk_state=risk_state,
        )
        
        # 正常情况
        can_trade, reason = await context.check_risk()
        assert can_trade is True
        
        # 风控锁定
        risk_state.lock("测试锁定")
        can_trade, reason = await context.check_risk()
        assert can_trade is False
        assert "测试锁定" in reason
    
    @pytest.mark.asyncio
    async def test_check_risk_drawdown(self, user, exchange_config, risk_state):
        context = UserContext(
            user=user,
            config=exchange_config,
            risk_state=risk_state,
        )
        
        # 回撤超限
        risk_state.current_drawdown = 0.25
        can_trade, reason = await context.check_risk()
        assert can_trade is False
        assert "回撤" in reason
