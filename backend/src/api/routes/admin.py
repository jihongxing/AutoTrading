"""
BTC 自动交易系统 — 管理后台 API

用户管理、系统统计、收益报表。
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...billing import ProfitTracker
from ...common.logging import get_logger
from ...common.utils import utc_now
from ...user.manager import UserManager
from ...user.models import SubscriptionPlan, UserStatus
from ..auth import CurrentAdmin, get_user_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["管理后台"])

# 收益跟踪器（应通过依赖注入）
_profit_tracker: ProfitTracker | None = None


def get_profit_tracker() -> ProfitTracker:
    global _profit_tracker
    if _profit_tracker is None:
        _profit_tracker = ProfitTracker()
    return _profit_tracker


# ========================================
# 请求模型
# ========================================

class SuspendRequest(BaseModel):
    """暂停用户请求"""
    reason: str = Field(description="暂停原因")


class UpdateSubscriptionRequest(BaseModel):
    """更新订阅请求"""
    subscription: SubscriptionPlan = Field(description="订阅计划")


# ========================================
# 用户管理接口
# ========================================

@router.get("/users", response_model=dict[str, Any])
async def list_users(
    admin: CurrentAdmin,
    status_filter: UserStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """获取用户列表"""
    manager = get_user_manager()
    users = await manager.list_users(status=status_filter)
    
    # 分页
    total = len(users)
    users = users[offset:offset + limit]
    
    return {
        "success": True,
        "data": {
            "users": [u.to_dict() for u in users],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
        "timestamp": utc_now().isoformat(),
    }


@router.get("/users/{user_id}", response_model=dict[str, Any])
async def get_user(
    user_id: str,
    admin: CurrentAdmin,
) -> dict[str, Any]:
    """获取用户详情"""
    manager = get_user_manager()
    user = await manager.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    # 获取关联数据
    exchange_config = await manager.get_exchange_config(user_id)
    risk_state = await manager.get_risk_state(user_id)
    
    return {
        "success": True,
        "data": {
            "user": user.to_dict(),
            "exchange_config": exchange_config.to_dict() if exchange_config else None,
            "risk_state": risk_state.to_dict() if risk_state else None,
        },
        "timestamp": utc_now().isoformat(),
    }


@router.post("/users/{user_id}/suspend", response_model=dict[str, Any])
async def suspend_user(
    user_id: str,
    request: SuspendRequest,
    admin: CurrentAdmin,
) -> dict[str, Any]:
    """暂停用户"""
    manager = get_user_manager()
    
    success = await manager.suspend_user(user_id, request.reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    logger.warning(f"管理员暂停用户: {user_id}, reason={request.reason}, admin={admin.user_id}")
    
    return {
        "success": True,
        "data": {"message": "用户已暂停", "user_id": user_id},
        "timestamp": utc_now().isoformat(),
    }


@router.post("/users/{user_id}/activate", response_model=dict[str, Any])
async def activate_user(
    user_id: str,
    admin: CurrentAdmin,
) -> dict[str, Any]:
    """激活用户"""
    manager = get_user_manager()
    
    success = await manager.activate_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    logger.info(f"管理员激活用户: {user_id}, admin={admin.user_id}")
    
    return {
        "success": True,
        "data": {"message": "用户已激活", "user_id": user_id},
        "timestamp": utc_now().isoformat(),
    }


@router.put("/users/{user_id}/subscription", response_model=dict[str, Any])
async def update_subscription(
    user_id: str,
    request: UpdateSubscriptionRequest,
    admin: CurrentAdmin,
) -> dict[str, Any]:
    """更新用户订阅"""
    manager = get_user_manager()
    
    success = await manager.update_user(user_id, subscription=request.subscription)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    logger.info(f"管理员更新订阅: {user_id}, plan={request.subscription}, admin={admin.user_id}")
    
    return {
        "success": True,
        "data": {"message": "订阅已更新", "subscription": request.subscription.value},
        "timestamp": utc_now().isoformat(),
    }


@router.post("/users/{user_id}/risk/lock", response_model=dict[str, Any])
async def lock_user_risk(
    user_id: str,
    request: SuspendRequest,
    admin: CurrentAdmin,
) -> dict[str, Any]:
    """锁定用户风控"""
    manager = get_user_manager()
    
    success = await manager.lock_user_risk(user_id, request.reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    return {
        "success": True,
        "data": {"message": "风控已锁定"},
        "timestamp": utc_now().isoformat(),
    }


@router.post("/users/{user_id}/risk/unlock", response_model=dict[str, Any])
async def unlock_user_risk(
    user_id: str,
    admin: CurrentAdmin,
) -> dict[str, Any]:
    """解锁用户风控"""
    manager = get_user_manager()
    
    success = await manager.unlock_user_risk(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )
    
    return {
        "success": True,
        "data": {"message": "风控已解锁"},
        "timestamp": utc_now().isoformat(),
    }


# ========================================
# 统计接口
# ========================================

@router.get("/stats", response_model=dict[str, Any])
async def get_stats(admin: CurrentAdmin) -> dict[str, Any]:
    """获取系统统计"""
    manager = get_user_manager()
    
    user_stats = manager.get_user_count()
    tradeable = await manager.get_tradeable_users()
    
    return {
        "success": True,
        "data": {
            "users": user_stats,
            "tradeable_users": len(tradeable),
        },
        "timestamp": utc_now().isoformat(),
    }


@router.get("/profit", response_model=dict[str, Any])
async def get_platform_profit(admin: CurrentAdmin) -> dict[str, Any]:
    """获取平台收益"""
    tracker = get_profit_tracker()
    
    total_fees = tracker.get_platform_total_fees()
    all_profits = tracker.get_all_profits()
    
    user_count = len(all_profits)
    trade_count = sum(len(p) for p in all_profits.values())
    
    return {
        "success": True,
        "data": {
            "total_platform_fees": total_fees,
            "user_count": user_count,
            "trade_count": trade_count,
        },
        "timestamp": utc_now().isoformat(),
    }


@router.get("/profit/{user_id}", response_model=dict[str, Any])
async def get_user_profit(
    user_id: str,
    admin: CurrentAdmin,
    period: str = "monthly",
) -> dict[str, Any]:
    """获取用户收益"""
    tracker = get_profit_tracker()
    
    if period == "daily":
        summary = tracker.calculate_daily_profit(user_id)
    elif period == "weekly":
        summary = tracker.calculate_weekly_profit(user_id)
    else:
        summary = tracker.calculate_monthly_profit(user_id)
    
    return {
        "success": True,
        "data": {"summary": summary.to_dict()},
        "timestamp": utc_now().isoformat(),
    }
