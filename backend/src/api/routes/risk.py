"""
BTC 自动交易系统 — 风控路由

提供风控状态查询和管理接口。
"""

from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from src.api.auth import CurrentUser, CurrentAdmin, audit_log
from src.api.dependencies import RiskEngineDep
from src.api.schemas import (
    ApiResponse,
    RiskEventResponse,
    RiskStatusResponse,
    UnlockRequest,
)
from src.common.enums import RiskLevel
from src.common.utils import utc_now

router = APIRouter(prefix="/risk", tags=["风控"])


@router.get("/status", response_model=ApiResponse[RiskStatusResponse])
async def get_risk_status(
    user: CurrentUser,
    risk_engine: RiskEngineDep,
) -> ApiResponse[RiskStatusResponse]:
    """
    获取风控状态
    
    返回当前风控级别、锁定状态和最近事件。
    """
    # 获取风控状态
    is_locked = risk_engine.is_locked
    lock_reason = risk_engine.lock_reason if is_locked else None
    
    # 简化：实际应从风控引擎获取
    recent_events = []
    
    response = RiskStatusResponse(
        level=RiskLevel.NORMAL if not is_locked else RiskLevel.CRITICAL,
        is_locked=is_locked,
        lock_reason=lock_reason,
        lock_since=utc_now() if is_locked else None,
        recent_events=recent_events,
        daily_loss=0.0,
        current_drawdown=0.0,
    )
    
    return ApiResponse(data=response)


@router.get("/events", response_model=ApiResponse[list[RiskEventResponse]])
async def get_risk_events(
    user: CurrentUser,
    risk_engine: RiskEngineDep,
    limit: int = 50,
    severity: RiskLevel | None = None,
) -> ApiResponse[list[RiskEventResponse]]:
    """
    获取风控事件
    
    返回最近的风控事件列表。
    """
    # 简化实现：实际应从存储获取
    events = [
        RiskEventResponse(
            event_id=str(uuid4()),
            timestamp=utc_now() - timedelta(hours=1),
            event_type="daily_loss_warning",
            severity=RiskLevel.WARNING,
            message="日亏损接近阈值",
            details={"current_loss": 0.025, "threshold": 0.03},
        ),
    ]
    
    # 按严重程度过滤
    if severity:
        events = [e for e in events if e.severity == severity]
    
    return ApiResponse(data=events[:limit])


@router.post("/unlock", response_model=ApiResponse[RiskStatusResponse])
async def request_unlock(
    admin: CurrentAdmin,
    risk_engine: RiskEngineDep,
    request: UnlockRequest,
) -> ApiResponse[RiskStatusResponse]:
    """
    请求解锁
    
    需要管理员权限。尝试解除风控锁定。
    """
    audit_log.log(
        api_key=admin.user_id,
        action="request_unlock",
        resource="risk_engine",
        details={"reason": request.reason},
    )
    
    if not risk_engine.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NOT_LOCKED", "message": "系统未被锁定"},
        )
    
    # 尝试解锁
    try:
        risk_engine.unlock(request.reason)
        
        response = RiskStatusResponse(
            level=RiskLevel.NORMAL,
            is_locked=False,
            lock_reason=None,
            lock_since=None,
            recent_events=[],
            daily_loss=0.0,
            current_drawdown=0.0,
        )
        
        return ApiResponse(data=response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNLOCK_DENIED", "message": str(e)},
        )
