"""
用户管理器单元测试
"""

import pytest

from src.user.manager import UserManager
from src.user.models import SubscriptionPlan, UserStatus
from src.user.storage import UserStorage


class TestUserManager:
    """用户管理器测试"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        storage = UserStorage(str(tmp_path / "users"))
        return UserManager(storage)
    
    @pytest.mark.asyncio
    async def test_create_user(self, manager):
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed_password",
        )
        
        assert user.email == "test@example.com"
        assert user.status == UserStatus.ACTIVE
        assert user.subscription == SubscriptionPlan.FREE
        assert user.trial_ends_at is not None
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, manager):
        await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
        )
        
        with pytest.raises(ValueError, match="邮箱已存在"):
            await manager.create_user(
                email="test@example.com",
                password_hash="hashed",
            )
    
    @pytest.mark.asyncio
    async def test_get_user(self, manager):
        created = await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
        )
        
        user = await manager.get_user(created.user_id)
        assert user is not None
        assert user.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, manager):
        await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
        )
        
        user = await manager.get_user_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"
        
        # 不存在的邮箱
        user = await manager.get_user_by_email("notfound@example.com")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update_user(self, manager):
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
        )
        
        success = await manager.update_user(
            user.user_id,
            email="new@example.com",
        )
        
        assert success is True
        
        updated = await manager.get_user(user.user_id)
        assert updated.email == "new@example.com"
    
    @pytest.mark.asyncio
    async def test_suspend_activate_user(self, manager):
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
        )
        
        # 暂停
        success = await manager.suspend_user(user.user_id, "测试暂停")
        assert success is True
        
        suspended = await manager.get_user(user.user_id)
        assert suspended.status == UserStatus.SUSPENDED
        
        # 激活
        success = await manager.activate_user(user.user_id)
        assert success is True
        
        activated = await manager.get_user(user.user_id)
        assert activated.status == UserStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_list_users(self, manager):
        await manager.create_user(email="user1@example.com", password_hash="h1")
        await manager.create_user(email="user2@example.com", password_hash="h2")
        
        users = await manager.list_users()
        assert len(users) == 2
    
    @pytest.mark.asyncio
    async def test_list_active_users(self, manager):
        user1 = await manager.create_user(email="user1@example.com", password_hash="h1")
        user2 = await manager.create_user(email="user2@example.com", password_hash="h2")
        
        await manager.suspend_user(user2.user_id, "测试")
        
        active = await manager.list_active_users()
        assert len(active) == 1
        assert active[0].user_id == user1.user_id
    
    @pytest.mark.asyncio
    async def test_set_exchange_config(self, manager):
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
        )
        
        config = await manager.set_exchange_config(
            user_id=user.user_id,
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
        )
        
        assert config.user_id == user.user_id
        assert config.testnet is True
        assert config.is_valid is False
    
    @pytest.mark.asyncio
    async def test_get_exchange_config(self, manager):
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
        )
        
        await manager.set_exchange_config(
            user_id=user.user_id,
            api_key="test_key",
            api_secret="test_secret",
        )
        
        config = await manager.get_exchange_config(user.user_id)
        assert config is not None
    
    @pytest.mark.asyncio
    async def test_risk_state(self, manager):
        user = await manager.create_user(
            email="test@example.com",
            password_hash="hashed",
        )
        
        # 创建用户时自动创建风控状态
        state = await manager.get_risk_state(user.user_id)
        assert state is not None
        assert state.is_locked is False
        
        # 锁定
        await manager.lock_user_risk(user.user_id, "测试锁定")
        state = await manager.get_risk_state(user.user_id)
        assert state.is_locked is True
        
        # 解锁
        await manager.unlock_user_risk(user.user_id)
        state = await manager.get_risk_state(user.user_id)
        assert state.is_locked is False
    
    @pytest.mark.asyncio
    async def test_get_user_count(self, manager):
        await manager.create_user(email="user1@example.com", password_hash="h1")
        user2 = await manager.create_user(email="user2@example.com", password_hash="h2")
        await manager.suspend_user(user2.user_id, "测试")
        
        stats = manager.get_user_count()
        
        assert stats["total"] == 2
        assert stats["active"] == 1
        assert stats["suspended"] == 1
