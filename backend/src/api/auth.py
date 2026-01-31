"""
BTC 自动交易系统 — 认证模块

JWT 用户认证、密码处理、权限检查。
"""

import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.common.logging import get_logger
from src.common.utils import utc_now
from src.user.models import User, UserStatus

logger = get_logger(__name__)

# ========================================
# 配置
# ========================================

# JWT 配置（生产环境应从环境变量读取）
JWT_SECRET = os.getenv("JWT_SECRET", "btc-trading-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


class Permission(str, Enum):
    """权限级别"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class TokenType(str, Enum):
    """Token 类型"""
    ACCESS = "access"
    REFRESH = "refresh"


# ========================================
# 密码处理
# ========================================

def hash_password(password: str) -> str:
    """
    哈希密码
    
    Args:
        password: 明文密码
    
    Returns:
        bcrypt 哈希
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    """
    验证密码
    
    Args:
        password: 明文密码
        hashed: 哈希值
    
    Returns:
        是否匹配
    """
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ========================================
# JWT Token
# ========================================

def create_access_token(
    user_id: str,
    email: str,
    is_admin: bool = False,
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建访问 Token
    
    Args:
        user_id: 用户 ID
        email: 邮箱
        is_admin: 是否管理员
        expires_delta: 过期时间
    
    Returns:
        JWT Token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = utc_now() + expires_delta
    
    payload = {
        "sub": user_id,
        "email": email,
        "is_admin": is_admin,
        "type": TokenType.ACCESS.value,
        "exp": expire,
        "iat": utc_now(),
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    创建刷新 Token
    
    Args:
        user_id: 用户 ID
    
    Returns:
        JWT Token
    """
    expire = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": user_id,
        "type": TokenType.REFRESH.value,
        "exp": expire,
        "iat": utc_now(),
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str, token_type: TokenType = TokenType.ACCESS) -> dict[str, Any]:
    """
    验证 Token
    
    Args:
        token: JWT Token
        token_type: 期望的 Token 类型
    
    Returns:
        Token payload
    
    Raises:
        HTTPException: Token 无效
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # 检查 Token 类型
        if payload.get("type") != token_type.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN_TYPE", "message": "Token 类型错误"},
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Token 已过期"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token 验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "无效的 Token"},
        )


# ========================================
# FastAPI 依赖
# ========================================

# Bearer Token 提取器
security = HTTPBearer(auto_error=False)

# 用户管理器引用（延迟导入避免循环依赖）
_user_manager = None


def set_user_manager(manager) -> None:
    """设置用户管理器（应用启动时调用）"""
    global _user_manager
    _user_manager = manager


def get_user_manager():
    """获取用户管理器"""
    if _user_manager is None:
        from src.user.manager import UserManager
        return UserManager()
    return _user_manager


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> User:
    """
    获取当前用户
    
    从 Authorization Header 提取 Bearer Token 并验证。
    
    Returns:
        当前用户
    
    Raises:
        HTTPException: 认证失败
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "缺少认证 Token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证 Token
    payload = verify_token(credentials.credentials, TokenType.ACCESS)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token 缺少用户信息"},
        )
    
    # 获取用户
    manager = get_user_manager()
    user = await manager.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    # 检查用户状态
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_SUSPENDED", "message": "用户已被暂停"},
        )
    
    if user.status == UserStatus.BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_BANNED", "message": "用户已被封禁"},
        )
    
    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """获取当前活跃用户"""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_INACTIVE", "message": "用户未激活"},
        )
    return user


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> User:
    """
    获取当前管理员用户
    
    Raises:
        HTTPException: 非管理员
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "缺少认证 Token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_token(credentials.credentials, TokenType.ACCESS)
    
    if not payload.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ADMIN_REQUIRED", "message": "需要管理员权限"},
        )
    
    user_id = payload.get("sub")
    manager = get_user_manager()
    user = await manager.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    return user


# ========================================
# 类型别名
# ========================================

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]


# ========================================
# Token 黑名单（简单实现，生产环境应使用 Redis）
# ========================================

_token_blacklist: set[str] = set()


def blacklist_token(token: str) -> None:
    """将 Token 加入黑名单"""
    _token_blacklist.add(token)


def is_token_blacklisted(token: str) -> bool:
    """检查 Token 是否在黑名单"""
    return token in _token_blacklist


# ========================================
# 旧版 API Key 认证（保留兼容）
# ========================================

class ApiKey:
    """API Key 信息"""
    
    def __init__(
        self,
        key: str,
        name: str,
        permissions: list[Permission],
        is_active: bool = True,
    ):
        self.key = key
        self.name = name
        self.permissions = permissions
        self.is_active = is_active


# 模拟 API Key 存储
_API_KEYS: dict[str, ApiKey] = {
    "dev-key-001": ApiKey(
        key="dev-key-001",
        name="Development Key",
        permissions=[Permission.READ, Permission.WRITE],
    ),
    "admin-key-001": ApiKey(
        key="admin-key-001",
        name="Admin Key",
        permissions=[Permission.READ, Permission.WRITE, Permission.ADMIN],
    ),
}


async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> ApiKey:
    """验证 API Key（旧版兼容）"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_API_KEY", "message": "缺少 API Key"},
        )
    
    api_key = _API_KEYS.get(x_api_key)
    
    if not api_key or not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY", "message": "无效的 API Key"},
        )
    
    return api_key


def require_permission(required: Permission):
    """权限检查装饰器"""
    async def check_permission(
        api_key: Annotated[ApiKey, Depends(verify_api_key)],
    ) -> ApiKey:
        if required not in api_key.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERMISSION_DENIED", "message": f"需要 {required.value} 权限"},
            )
        return api_key
    
    return check_permission


RequireRead = Annotated[ApiKey, Depends(require_permission(Permission.READ))]
RequireWrite = Annotated[ApiKey, Depends(require_permission(Permission.WRITE))]
RequireAdmin = Annotated[ApiKey, Depends(require_permission(Permission.ADMIN))]


# ========================================
# 审计日志
# ========================================

class AuditLog:
    """审计日志"""
    
    def __init__(self):
        self._logs: list[dict] = []
    
    def log(
        self,
        api_key: str,
        action: str,
        resource: str,
        details: dict | None = None,
        success: bool = True,
    ) -> None:
        """记录审计日志"""
        entry = {
            "timestamp": utc_now().isoformat(),
            "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
            "action": action,
            "resource": resource,
            "details": details,
            "success": success,
        }
        self._logs.append(entry)
        
        logger.info(
            f"审计日志: {action} {resource}",
            extra={"api_key": api_key[:8] if len(api_key) > 8 else api_key, "action": action, "resource": resource},
        )
    
    def get_logs(self, limit: int = 100) -> list[dict]:
        """获取审计日志"""
        return self._logs[-limit:]


# 全局审计日志实例
audit_log = AuditLog()
