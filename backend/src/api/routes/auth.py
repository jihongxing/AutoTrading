"""
BTC 自动交易系统 — 认证 API

用户注册、登录、Token 刷新、登出。
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from ...common.logging import get_logger
from ...common.utils import utc_now
from ...user.manager import UserManager
from ...user.models import SubscriptionPlan
from ..auth import (
    TokenType,
    blacklist_token,
    create_access_token,
    create_refresh_token,
    get_user_manager,
    hash_password,
    is_token_blacklisted,
    verify_password,
    verify_token,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


# ========================================
# 请求/响应模型
# ========================================

class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr = Field(description="邮箱")
    password: str = Field(min_length=8, max_length=128, description="密码")
    subscription: SubscriptionPlan = Field(default=SubscriptionPlan.FREE, description="订阅计划")


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr = Field(description="邮箱")
    password: str = Field(description="密码")


class RefreshRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(description="刷新 Token")


class LogoutRequest(BaseModel):
    """登出请求"""
    access_token: str = Field(description="访问 Token")
    refresh_token: str | None = Field(default=None, description="刷新 Token")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒


# ========================================
# API 接口
# ========================================

@router.post("/register", response_model=dict[str, Any])
async def register(request: RegisterRequest) -> dict[str, Any]:
    """
    用户注册
    
    创建新用户账户。
    """
    manager = get_user_manager()
    
    # 检查邮箱是否已存在
    existing = await manager.get_user_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMAIL_EXISTS", "message": "邮箱已被注册"},
        )
    
    # 哈希密码
    password_hash = hash_password(request.password)
    
    # 创建用户
    try:
        user = await manager.create_user(
            email=request.email,
            password_hash=password_hash,
            subscription=request.subscription,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CREATE_FAILED", "message": str(e)},
        )
    
    # 生成 Token
    access_token = create_access_token(user.user_id, user.email)
    refresh_token = create_refresh_token(user.user_id)
    
    logger.info(f"用户注册成功: {user.user_id}, email={user.email}")
    
    return {
        "success": True,
        "data": {
            "user": user.to_dict(),
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,
            },
        },
        "timestamp": utc_now().isoformat(),
    }


@router.post("/login", response_model=dict[str, Any])
async def login(request: LoginRequest) -> dict[str, Any]:
    """
    用户登录
    
    验证凭据并返回 Token。
    """
    manager = get_user_manager()
    
    # 查找用户
    user = await manager.get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "邮箱或密码错误"},
        )
    
    # 验证密码
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"登录失败（密码错误）: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "邮箱或密码错误"},
        )
    
    # 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_INACTIVE", "message": "用户未激活或已被禁用"},
        )
    
    # 生成 Token
    access_token = create_access_token(user.user_id, user.email, user.is_admin)
    refresh_token = create_refresh_token(user.user_id)
    
    logger.info(f"用户登录成功: {user.user_id}")
    
    return {
        "success": True,
        "data": {
            "user": user.to_dict(),
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,
            },
        },
        "timestamp": utc_now().isoformat(),
    }


@router.post("/refresh", response_model=dict[str, Any])
async def refresh(request: RefreshRequest) -> dict[str, Any]:
    """
    刷新 Token
    
    使用 refresh_token 获取新的 access_token。
    """
    # 检查黑名单
    if is_token_blacklisted(request.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_REVOKED", "message": "Token 已被撤销"},
        )
    
    # 验证 refresh_token
    payload = verify_token(request.refresh_token, TokenType.REFRESH)
    user_id = payload.get("sub")
    
    # 获取用户
    manager = get_user_manager()
    user = await manager.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_INACTIVE", "message": "用户未激活"},
        )
    
    # 生成新 Token
    access_token = create_access_token(user.user_id, user.email, user.is_admin)
    new_refresh_token = create_refresh_token(user.user_id)
    
    # 旧 refresh_token 加入黑名单
    blacklist_token(request.refresh_token)
    
    return {
        "success": True,
        "data": {
            "tokens": {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,
            },
        },
        "timestamp": utc_now().isoformat(),
    }


@router.post("/logout", response_model=dict[str, Any])
async def logout(request: LogoutRequest) -> dict[str, Any]:
    """
    用户登出
    
    将 Token 加入黑名单。
    """
    # 将 Token 加入黑名单
    blacklist_token(request.access_token)
    if request.refresh_token:
        blacklist_token(request.refresh_token)
    
    logger.info("用户已登出")
    
    return {
        "success": True,
        "data": {"message": "已成功登出"},
        "timestamp": utc_now().isoformat(),
    }


@router.post("/change-password", response_model=dict[str, Any])
async def change_password(
    old_password: str,
    new_password: str,
    user_id: str,  # 实际应从 Token 获取
) -> dict[str, Any]:
    """
    修改密码
    """
    manager = get_user_manager()
    user = await manager.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    # 验证旧密码
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WRONG_PASSWORD", "message": "原密码错误"},
        )
    
    # 更新密码
    new_hash = hash_password(new_password)
    await manager.update_user(user_id, password_hash=new_hash)
    
    logger.info(f"密码已修改: {user_id}")
    
    return {
        "success": True,
        "data": {"message": "密码已修改"},
        "timestamp": utc_now().isoformat(),
    }
