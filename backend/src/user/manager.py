"""
BTC 自动交易系统 — 用户管理器
"""

import uuid
from datetime import timedelta

from src.common.logging import get_logger
from src.common.utils import utc_now

from .crypto import decrypt_api_key, encrypt_api_key
from .models import (
    PLAN_CONFIG,
    SubscriptionPlan,
    User,
    UserExchangeConfig,
    UserRiskState,
    UserStatus,
)
from .storage import UserStorage

logger = get_logger(__name__)


class UserManager:
    """
    用户管理器
    
    提供用户 CRUD、交易所配置、API Key 验证等功能。
    """
    
    def __init__(self, storage: UserStorage | None = None):
        self.storage = storage or UserStorage()
    
    # ========================================
    # 用户管理
    # ========================================
    
    async def create_user(
        self,
        email: str,
        password_hash: str,
        subscription: SubscriptionPlan = SubscriptionPlan.FREE,
    ) -> User:
        """
        创建用户
        
        Args:
            email: 邮箱
            password_hash: 密码哈希（调用方负责哈希）
            subscription: 订阅计划
        
        Returns:
            新创建的用户
        
        Raises:
            ValueError: 邮箱已存在
        """
        # 检查邮箱唯一性
        existing = self.storage.get_user_by_email(email)
        if existing:
            raise ValueError(f"邮箱已存在: {email}")
        
        # 计算试用期
        trial_ends_at = None
        if subscription == SubscriptionPlan.FREE:
            trial_days = PLAN_CONFIG[subscription]["trial_days"]
            trial_ends_at = utc_now() + timedelta(days=trial_days)
        
        user = User(
            user_id=str(uuid.uuid4()),
            email=email,
            password_hash=password_hash,
            status=UserStatus.ACTIVE,  # 简化：直接激活
            subscription=subscription,
            trial_ends_at=trial_ends_at,
        )
        
        self.storage.save_user(user)
        
        # 创建风控状态
        risk_state = UserRiskState(user_id=user.user_id)
        self.storage.save_risk_state(risk_state)
        
        logger.info(f"用户已创建: {user.user_id}, email={email}")
        return user
    
    async def get_user(self, user_id: str) -> User | None:
        """获取用户"""
        return self.storage.get_user(user_id)
    
    async def get_user_by_email(self, email: str) -> User | None:
        """通过邮箱获取用户"""
        return self.storage.get_user_by_email(email)
    
    async def update_user(self, user_id: str, **kwargs) -> bool:
        """
        更新用户
        
        Args:
            user_id: 用户 ID
            **kwargs: 要更新的字段
        
        Returns:
            是否成功
        """
        user = self.storage.get_user(user_id)
        if not user:
            return False
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = utc_now()
        self.storage.save_user(user)
        return True
    
    async def list_users(self, status: UserStatus | None = None) -> list[User]:
        """列出用户"""
        return self.storage.list_users(status)
    
    async def list_active_users(self) -> list[User]:
        """列出活跃用户"""
        return self.storage.list_active_users()
    
    async def suspend_user(self, user_id: str, reason: str) -> bool:
        """暂停用户"""
        user = self.storage.get_user(user_id)
        if not user:
            return False
        
        user.status = UserStatus.SUSPENDED
        user.updated_at = utc_now()
        self.storage.save_user(user)
        
        logger.warning(f"用户已暂停: {user_id}, reason={reason}")
        return True
    
    async def activate_user(self, user_id: str) -> bool:
        """激活用户"""
        user = self.storage.get_user(user_id)
        if not user:
            return False
        
        user.status = UserStatus.ACTIVE
        user.updated_at = utc_now()
        self.storage.save_user(user)
        
        logger.info(f"用户已激活: {user_id}")
        return True
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        # 删除关联数据
        self.storage.delete_exchange_config(user_id)
        self.storage.delete_risk_state(user_id)
        
        return self.storage.delete_user(user_id)
    
    # ========================================
    # 交易所配置
    # ========================================
    
    async def set_exchange_config(
        self,
        user_id: str,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        leverage: int = 10,
        max_position_pct: float | None = None,
    ) -> UserExchangeConfig:
        """
        设置交易所配置
        
        Args:
            user_id: 用户 ID
            api_key: API Key（明文）
            api_secret: API Secret（明文）
            testnet: 是否测试网
            leverage: 杠杆倍数
            max_position_pct: 最大仓位比例（None 则使用订阅计划默认值）
        
        Returns:
            交易所配置
        """
        user = self.storage.get_user(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
        
        # 使用订阅计划的最大仓位限制
        if max_position_pct is None:
            max_position_pct = user.max_position_pct
        else:
            # 不能超过订阅计划限制
            max_position_pct = min(max_position_pct, user.max_position_pct)
        
        config = UserExchangeConfig(
            user_id=user_id,
            api_key_encrypted=encrypt_api_key(api_key),
            api_secret_encrypted=encrypt_api_key(api_secret),
            testnet=testnet,
            leverage=leverage,
            max_position_pct=max_position_pct,
            is_valid=False,  # 需要验证
        )
        
        self.storage.save_exchange_config(config)
        logger.info(f"交易所配置已保存: {user_id}")
        return config
    
    async def get_exchange_config(self, user_id: str) -> UserExchangeConfig | None:
        """获取交易所配置"""
        return self.storage.get_exchange_config(user_id)
    
    async def delete_exchange_config(self, user_id: str) -> bool:
        """删除交易所配置"""
        return self.storage.delete_exchange_config(user_id)
    
    async def verify_api_key(self, user_id: str) -> tuple[bool, str]:
        """
        验证 API Key
        
        Args:
            user_id: 用户 ID
        
        Returns:
            (是否有效, 错误信息)
        """
        config = self.storage.get_exchange_config(user_id)
        if not config:
            return False, "未配置交易所"
        
        try:
            # 解密 API Key
            api_key = decrypt_api_key(config.api_key_encrypted)
            api_secret = decrypt_api_key(config.api_secret_encrypted)
            
            if not api_key or not api_secret:
                return False, "API Key 为空"
            
            # 创建临时客户端验证
            from src.core.execution.exchange.binance import BinanceClient
            
            client = BinanceClient(
                api_key=api_key,
                api_secret=api_secret,
                testnet=config.testnet,
            )
            
            await client.connect()
            
            try:
                # 尝试获取账户信息
                balance = await client.get_balance()
                
                # 验证成功
                config.is_valid = True
                config.last_verified_at = utc_now()
                config.updated_at = utc_now()
                self.storage.save_exchange_config(config)
                
                logger.info(f"API Key 验证成功: {user_id}, balance={balance}")
                return True, ""
                
            finally:
                await client.disconnect()
                
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"API Key 验证失败: {user_id}, error={error_msg}")
            
            # 标记为无效
            config.is_valid = False
            config.updated_at = utc_now()
            self.storage.save_exchange_config(config)
            
            return False, error_msg
    
    def get_decrypted_keys(self, user_id: str) -> tuple[str, str] | None:
        """
        获取解密后的 API Key
        
        Args:
            user_id: 用户 ID
        
        Returns:
            (api_key, api_secret) 或 None
        """
        config = self.storage.get_exchange_config(user_id)
        if not config:
            return None
        
        api_key = decrypt_api_key(config.api_key_encrypted)
        api_secret = decrypt_api_key(config.api_secret_encrypted)
        
        return api_key, api_secret
    
    # ========================================
    # 风控状态
    # ========================================
    
    async def get_risk_state(self, user_id: str) -> UserRiskState | None:
        """获取风控状态"""
        return self.storage.get_risk_state(user_id)
    
    async def get_or_create_risk_state(self, user_id: str) -> UserRiskState:
        """获取或创建风控状态"""
        return self.storage.get_or_create_risk_state(user_id)
    
    async def update_risk_state(self, state: UserRiskState) -> None:
        """更新风控状态"""
        self.storage.save_risk_state(state)
    
    async def lock_user_risk(self, user_id: str, reason: str) -> bool:
        """锁定用户风控"""
        state = self.storage.get_risk_state(user_id)
        if not state:
            return False
        
        state.lock(reason)
        self.storage.save_risk_state(state)
        
        logger.warning(f"用户风控已锁定: {user_id}, reason={reason}")
        return True
    
    async def unlock_user_risk(self, user_id: str) -> bool:
        """解锁用户风控"""
        state = self.storage.get_risk_state(user_id)
        if not state:
            return False
        
        state.unlock()
        self.storage.save_risk_state(state)
        
        logger.info(f"用户风控已解锁: {user_id}")
        return True
    
    # ========================================
    # 批量操作
    # ========================================
    
    async def get_tradeable_users(self) -> list[tuple[User, UserExchangeConfig, UserRiskState]]:
        """
        获取可交易的用户列表
        
        返回满足以下条件的用户：
        - 状态为 ACTIVE
        - 交易所配置有效
        - 风控未锁定
        - 试用期未过期
        """
        result = []
        
        for user in self.storage.list_active_users():
            # 检查试用期
            if user.is_trial_expired:
                continue
            
            # 检查交易所配置
            config = self.storage.get_exchange_config(user.user_id)
            if not config or not config.is_valid:
                continue
            
            # 检查风控状态
            risk_state = self.storage.get_risk_state(user.user_id)
            if not risk_state:
                risk_state = UserRiskState(user_id=user.user_id)
            
            if risk_state.is_locked:
                continue
            
            result.append((user, config, risk_state))
        
        return result
    
    def get_user_count(self) -> dict[str, int]:
        """获取用户统计"""
        users = self.storage.list_users()
        
        stats = {
            "total": len(users),
            "active": 0,
            "suspended": 0,
            "pending": 0,
        }
        
        for user in users:
            if user.status == UserStatus.ACTIVE:
                stats["active"] += 1
            elif user.status == UserStatus.SUSPENDED:
                stats["suspended"] += 1
            elif user.status == UserStatus.PENDING:
                stats["pending"] += 1
        
        return stats
