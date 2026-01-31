"""
多用户流程集成测试
"""

import pytest

from src.billing import ProfitTracker
from src.user.context import TradingSignal, UserContext
from src.user.manager import UserManager
from src.user.models import SubscriptionPlan, User, UserExchangeConfig, UserRiskState, UserStatus
from src.user.storage import UserStorage


class TestMultiUserFlow:
    """多用户流程测试"""
    
    @pytest.fixture
    def storage(self, tmp_path):
        return UserStorage(str(tmp_path / "users"))
    
    @pytest.fixture
    def manager(self, storage):
        return UserManager(storage)
    
    @pytest.mark.asyncio
    async def test_user_registration_flow(self, manager):
        """测试用户注册流程"""
        # 注册
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed_password",
            subscription=SubscriptionPlan.FREE,
        )
        
        assert user.status == UserStatus.ACTIVE
        assert user.subscription == SubscriptionPlan.FREE
        assert user.trial_ends_at is not None
        
        # 风控状态自动创建
        risk_state = await manager.get_risk_state(user.user_id)
        assert risk_state is not None
        assert risk_state.is_locked is False
    
    @pytest.mark.asyncio
    async def test_api_key_binding_flow(self, manager):
        """测试 API Key 绑定流程"""
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
        )
        
        # 设置交易所配置
        config = await manager.set_exchange_config(
            user_id=user.user_id,
            api_key="test_api_key",
            api_secret="test_api_secret",
            testnet=True,
            leverage=10,
        )
        
        assert config.is_valid is False  # 未验证
        
        # 获取配置
        saved_config = await manager.get_exchange_config(user.user_id)
        assert saved_config is not None
        assert saved_config.testnet is True
    
    @pytest.mark.asyncio
    async def test_multi_user_context_creation(self, manager):
        """测试多用户上下文创建"""
        # 创建多个用户
        users = []
        for i in range(3):
            user = await manager.create_user(
                email=f"user{i}@example.com",
                password_hash="hashed",
            )
            await manager.set_exchange_config(
                user_id=user.user_id,
                api_key=f"key_{i}",
                api_secret=f"secret_{i}",
                testnet=True,
            )
            # 模拟验证通过
            config = await manager.get_exchange_config(user.user_id)
            config.is_valid = True
            manager.storage.save_exchange_config(config)
            users.append(user)
        
        # 获取可交易用户
        tradeable = await manager.get_tradeable_users()
        assert len(tradeable) == 3
        
        # 创建上下文
        contexts = []
        for user, config, risk_state in tradeable:
            ctx = UserContext(user, config, risk_state)
            contexts.append(ctx)
        
        assert len(contexts) == 3
    
    @pytest.mark.asyncio
    async def test_signal_routing(self, manager):
        """测试信号路由"""
        # 创建用户
        user1 = await manager.create_user(email="user1@example.com", password_hash="h1")
        user2 = await manager.create_user(email="user2@example.com", password_hash="h2")
        
        # 配置交易所
        for user in [user1, user2]:
            await manager.set_exchange_config(
                user_id=user.user_id,
                api_key="key",
                api_secret="secret",
                testnet=True,
            )
            config = await manager.get_exchange_config(user.user_id)
            config.is_valid = True
            manager.storage.save_exchange_config(config)
        
        # 暂停 user2
        await manager.suspend_user(user2.user_id, "测试")
        
        # 获取可交易用户
        tradeable = await manager.get_tradeable_users()
        
        # 只有 user1 应该可交易
        assert len(tradeable) == 1
        assert tradeable[0][0].user_id == user1.user_id
    
    @pytest.mark.asyncio
    async def test_profit_tracking_flow(self, manager):
        """测试收益跟踪流程"""
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
            subscription=SubscriptionPlan.BASIC,
        )
        
        tracker = ProfitTracker()
        
        # 记录盈利交易
        profit1 = tracker.record_trade(
            user_id=user.user_id,
            trade_id="trade-001",
            symbol="BTCUSDT",
            side="BUY",
            realized_pnl=100.0,
            fee_rate=user.fee_rate,
        )
        
        assert profit1.platform_fee == 20.0  # BASIC 20%
        assert profit1.net_profit == 80.0
        
        # 记录亏损交易
        profit2 = tracker.record_trade(
            user_id=user.user_id,
            trade_id="trade-002",
            symbol="BTCUSDT",
            side="SELL",
            realized_pnl=-30.0,
            fee_rate=user.fee_rate,
        )
        
        assert profit2.platform_fee == 0.0  # 亏损不收费
        
        # 计算日收益
        summary = tracker.calculate_daily_profit(user.user_id)
        
        assert summary.total_trades == 2
        assert summary.net_pnl == 70.0
        assert summary.platform_fees == 20.0
    
    @pytest.mark.asyncio
    async def test_risk_isolation(self, manager):
        """测试风控隔离"""
        user1 = await manager.create_user(email="user1@example.com", password_hash="h1")
        user2 = await manager.create_user(email="user2@example.com", password_hash="h2")
        
        # 锁定 user1 风控
        await manager.lock_user_risk(user1.user_id, "连续亏损")
        
        # user1 被锁定
        state1 = await manager.get_risk_state(user1.user_id)
        assert state1.is_locked is True
        
        # user2 不受影响
        state2 = await manager.get_risk_state(user2.user_id)
        assert state2.is_locked is False
    
    @pytest.mark.asyncio
    async def test_subscription_upgrade(self, manager):
        """测试订阅升级"""
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
            subscription=SubscriptionPlan.FREE,
        )
        
        assert user.fee_rate == 0.30
        assert user.max_position_pct == 0.05
        
        # 升级到 PRO
        await manager.update_user(user.user_id, subscription=SubscriptionPlan.PRO)
        
        upgraded = await manager.get_user(user.user_id)
        assert upgraded.fee_rate == 0.10
        assert upgraded.max_position_pct == 0.30


class TestDataIsolation:
    """数据隔离测试"""
    
    @pytest.fixture
    def storage(self, tmp_path):
        return UserStorage(str(tmp_path / "users"))
    
    @pytest.fixture
    def manager(self, storage):
        return UserManager(storage)
    
    @pytest.mark.asyncio
    async def test_user_data_isolation(self, manager):
        """测试用户数据隔离"""
        user1 = await manager.create_user(email="user1@example.com", password_hash="h1")
        user2 = await manager.create_user(email="user2@example.com", password_hash="h2")
        
        # 设置不同配置
        await manager.set_exchange_config(
            user_id=user1.user_id,
            api_key="key1",
            api_secret="secret1",
            leverage=10,
        )
        await manager.set_exchange_config(
            user_id=user2.user_id,
            api_key="key2",
            api_secret="secret2",
            leverage=20,
        )
        
        # 验证隔离
        config1 = await manager.get_exchange_config(user1.user_id)
        config2 = await manager.get_exchange_config(user2.user_id)
        
        assert config1.leverage == 10
        assert config2.leverage == 20
    
    @pytest.mark.asyncio
    async def test_profit_data_isolation(self, manager):
        """测试收益数据隔离"""
        user1 = await manager.create_user(email="user1@example.com", password_hash="h1")
        user2 = await manager.create_user(email="user2@example.com", password_hash="h2")
        
        tracker = ProfitTracker()
        
        # user1 交易
        tracker.record_trade(
            user_id=user1.user_id,
            trade_id="t1",
            symbol="BTCUSDT",
            side="BUY",
            realized_pnl=100.0,
            fee_rate=0.20,
        )
        
        # user2 交易
        tracker.record_trade(
            user_id=user2.user_id,
            trade_id="t2",
            symbol="BTCUSDT",
            side="BUY",
            realized_pnl=200.0,
            fee_rate=0.10,
        )
        
        # 验证隔离
        profits1 = tracker.get_user_profits(user1.user_id)
        profits2 = tracker.get_user_profits(user2.user_id)
        
        assert len(profits1) == 1
        assert len(profits2) == 1
        assert profits1[0].realized_pnl == 100.0
        assert profits2[0].realized_pnl == 200.0
