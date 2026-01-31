"""
BTC 自动交易系统 — 用户存储

用户数据持久化。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.logging import get_logger
from src.common.utils import utc_now

from .models import (
    SubscriptionPlan,
    User,
    UserExchangeConfig,
    UserRiskState,
    UserStatus,
)

logger = get_logger(__name__)


class UserStorage:
    """
    用户存储
    
    当前实现：JSON 文件存储
    生产环境：应替换为 PostgreSQL
    """
    
    def __init__(self, data_dir: str = "data/users"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._users_file = self.data_dir / "users.json"
        self._configs_file = self.data_dir / "exchange_configs.json"
        self._risk_states_file = self.data_dir / "risk_states.json"
        
        # 内存缓存
        self._users: dict[str, User] = {}
        self._configs: dict[str, UserExchangeConfig] = {}
        self._risk_states: dict[str, UserRiskState] = {}
        
        # 加载数据
        self._load_all()
    
    def _load_all(self) -> None:
        """加载所有数据"""
        self._users = self._load_users()
        self._configs = self._load_configs()
        self._risk_states = self._load_risk_states()
    
    # ========================================
    # 用户 CRUD
    # ========================================
    
    def save_user(self, user: User) -> None:
        """保存用户"""
        self._users[user.user_id] = user
        self._save_users()
    
    def get_user(self, user_id: str) -> User | None:
        """获取用户"""
        return self._users.get(user_id)
    
    def get_user_by_email(self, email: str) -> User | None:
        """通过邮箱获取用户"""
        for user in self._users.values():
            if user.email == email:
                return user
        return None
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        if user_id in self._users:
            del self._users[user_id]
            self._save_users()
            return True
        return False
    
    def list_users(self, status: UserStatus | None = None) -> list[User]:
        """列出用户"""
        users = list(self._users.values())
        if status:
            users = [u for u in users if u.status == status]
        return users
    
    def list_active_users(self) -> list[User]:
        """列出活跃用户"""
        return self.list_users(UserStatus.ACTIVE)
    
    # ========================================
    # 交易所配置 CRUD
    # ========================================
    
    def save_exchange_config(self, config: UserExchangeConfig) -> None:
        """保存交易所配置"""
        self._configs[config.user_id] = config
        self._save_configs()
    
    def get_exchange_config(self, user_id: str) -> UserExchangeConfig | None:
        """获取交易所配置"""
        return self._configs.get(user_id)
    
    def delete_exchange_config(self, user_id: str) -> bool:
        """删除交易所配置"""
        if user_id in self._configs:
            del self._configs[user_id]
            self._save_configs()
            return True
        return False
    
    def list_valid_configs(self) -> list[UserExchangeConfig]:
        """列出有效的交易所配置"""
        return [c for c in self._configs.values() if c.is_valid]
    
    # ========================================
    # 风控状态 CRUD
    # ========================================
    
    def save_risk_state(self, state: UserRiskState) -> None:
        """保存风控状态"""
        self._risk_states[state.user_id] = state
        self._save_risk_states()
    
    def get_risk_state(self, user_id: str) -> UserRiskState | None:
        """获取风控状态"""
        return self._risk_states.get(user_id)
    
    def get_or_create_risk_state(self, user_id: str) -> UserRiskState:
        """获取或创建风控状态"""
        state = self._risk_states.get(user_id)
        if state is None:
            state = UserRiskState(user_id=user_id)
            self.save_risk_state(state)
        return state
    
    def delete_risk_state(self, user_id: str) -> bool:
        """删除风控状态"""
        if user_id in self._risk_states:
            del self._risk_states[user_id]
            self._save_risk_states()
            return True
        return False
    
    # ========================================
    # 序列化/反序列化
    # ========================================
    
    def _load_users(self) -> dict[str, User]:
        """加载用户数据"""
        if not self._users_file.exists():
            return {}
        
        try:
            with open(self._users_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            users = {}
            for item in data:
                user = User(
                    user_id=item["user_id"],
                    email=item["email"],
                    password_hash=item["password_hash"],
                    status=UserStatus(item["status"]),
                    subscription=SubscriptionPlan(item["subscription"]),
                    is_admin=item.get("is_admin", False),
                    trial_ends_at=datetime.fromisoformat(item["trial_ends_at"]) if item.get("trial_ends_at") else None,
                    created_at=datetime.fromisoformat(item["created_at"]),
                    updated_at=datetime.fromisoformat(item["updated_at"]),
                )
                users[user.user_id] = user
            return users
        except Exception as e:
            logger.error(f"加载用户数据失败: {e}")
            return {}
    
    def _save_users(self) -> None:
        """保存用户数据"""
        data = []
        for user in self._users.values():
            data.append({
                "user_id": user.user_id,
                "email": user.email,
                "password_hash": user.password_hash,
                "status": user.status.value,
                "subscription": user.subscription.value,
                "is_admin": user.is_admin,
                "trial_ends_at": user.trial_ends_at.isoformat() if user.trial_ends_at else None,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            })
        
        with open(self._users_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_configs(self) -> dict[str, UserExchangeConfig]:
        """加载交易所配置"""
        if not self._configs_file.exists():
            return {}
        
        try:
            with open(self._configs_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            configs = {}
            for item in data:
                config = UserExchangeConfig(
                    user_id=item["user_id"],
                    exchange=item.get("exchange", "binance"),
                    api_key_encrypted=item.get("api_key_encrypted", ""),
                    api_secret_encrypted=item.get("api_secret_encrypted", ""),
                    testnet=item.get("testnet", False),
                    leverage=item.get("leverage", 10),
                    max_position_pct=item.get("max_position_pct", 0.05),
                    is_valid=item.get("is_valid", False),
                    last_verified_at=datetime.fromisoformat(item["last_verified_at"]) if item.get("last_verified_at") else None,
                    created_at=datetime.fromisoformat(item["created_at"]) if item.get("created_at") else utc_now(),
                    updated_at=datetime.fromisoformat(item["updated_at"]) if item.get("updated_at") else utc_now(),
                )
                configs[config.user_id] = config
            return configs
        except Exception as e:
            logger.error(f"加载交易所配置失败: {e}")
            return {}
    
    def _save_configs(self) -> None:
        """保存交易所配置"""
        data = []
        for config in self._configs.values():
            data.append({
                "user_id": config.user_id,
                "exchange": config.exchange,
                "api_key_encrypted": config.api_key_encrypted,
                "api_secret_encrypted": config.api_secret_encrypted,
                "testnet": config.testnet,
                "leverage": config.leverage,
                "max_position_pct": config.max_position_pct,
                "is_valid": config.is_valid,
                "last_verified_at": config.last_verified_at.isoformat() if config.last_verified_at else None,
                "created_at": config.created_at.isoformat(),
                "updated_at": config.updated_at.isoformat(),
            })
        
        with open(self._configs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_risk_states(self) -> dict[str, UserRiskState]:
        """加载风控状态"""
        if not self._risk_states_file.exists():
            return {}
        
        try:
            with open(self._risk_states_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            states = {}
            for item in data:
                state = UserRiskState(
                    user_id=item["user_id"],
                    current_drawdown=item.get("current_drawdown", 0.0),
                    daily_loss=item.get("daily_loss", 0.0),
                    weekly_loss=item.get("weekly_loss", 0.0),
                    consecutive_losses=item.get("consecutive_losses", 0),
                    is_locked=item.get("is_locked", False),
                    locked_reason=item.get("locked_reason"),
                    locked_at=datetime.fromisoformat(item["locked_at"]) if item.get("locked_at") else None,
                    updated_at=datetime.fromisoformat(item["updated_at"]) if item.get("updated_at") else utc_now(),
                )
                states[state.user_id] = state
            return states
        except Exception as e:
            logger.error(f"加载风控状态失败: {e}")
            return {}
    
    def _save_risk_states(self) -> None:
        """保存风控状态"""
        data = []
        for state in self._risk_states.values():
            data.append({
                "user_id": state.user_id,
                "current_drawdown": state.current_drawdown,
                "daily_loss": state.daily_loss,
                "weekly_loss": state.weekly_loss,
                "consecutive_losses": state.consecutive_losses,
                "is_locked": state.is_locked,
                "locked_reason": state.locked_reason,
                "locked_at": state.locked_at.isoformat() if state.locked_at else None,
                "updated_at": state.updated_at.isoformat(),
            })
        
        with open(self._risk_states_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
