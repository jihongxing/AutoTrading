"""
BTC 自动交易系统 — 系统状态路由

提供系统状态查询和管理接口。
"""

from fastapi import APIRouter, HTTPException, status

from src.api.auth import CurrentUser, CurrentAdmin, audit_log
from src.api.dependencies import StateServiceDep
from src.api.schemas import (
    ApiResponse,
    ForceLockRequest,
    StateHistoryItem,
    StateHistoryResponse,
    StateResponse,
)
from src.common.enums import RiskLevel, SystemState
from src.common.utils import utc_now

router = APIRouter(prefix="/state", tags=["系统状态"])


@router.get("", response_model=ApiResponse[StateResponse])
async def get_current_state(
    user: CurrentUser,
    state_service: StateServiceDep,
) -> ApiResponse[StateResponse]:
    """
    获取当前系统状态
    
    返回系统当前状态、交易模式和风控级别。
    """
    state = state_service.get_current_state()
    regime = state_service.get_current_regime()
    
    response = StateResponse(
        current_state=state,
        current_regime=regime,
        is_trading_allowed=state_service.is_trading_allowed(),
        state_since=utc_now(),  # 简化：实际应从存储获取
        risk_level=RiskLevel.NORMAL,  # 简化：实际应从风控获取
    )
    
    return ApiResponse(data=response)


@router.get("/history", response_model=ApiResponse[StateHistoryResponse])
async def get_state_history(
    user: CurrentUser,
    state_service: StateServiceDep,
    limit: int = 50,
) -> ApiResponse[StateHistoryResponse]:
    """
    获取状态历史
    
    返回最近的状态变更记录。
    """
    # 简化实现：实际应从存储获取
    history = [
        StateHistoryItem(
            state=SystemState.OBSERVING,
            timestamp=utc_now(),
            reason="系统启动",
            triggered_by="system",
        )
    ]
    
    response = StateHistoryResponse(
        items=history[:limit],
        total=len(history),
    )
    
    return ApiResponse(data=response)


@router.post("/force-lock", response_model=ApiResponse[StateResponse])
async def force_lock_system(
    admin: CurrentAdmin,
    state_service: StateServiceDep,
    request: ForceLockRequest,
) -> ApiResponse[StateResponse]:
    """
    强制锁定系统
    
    需要管理员权限。将系统状态设置为 RISK_LOCKED。
    """
    audit_log.log(
        api_key=admin.user_id,
        action="force_lock",
        resource="system_state",
        details={"reason": request.reason},
    )
    
    try:
        await state_service.force_lock(request.reason)
        
        response = StateResponse(
            current_state=SystemState.RISK_LOCKED,
            current_regime=None,
            is_trading_allowed=False,
            state_since=utc_now(),
            risk_level=RiskLevel.RISK_LOCKED,
        )
        
        return ApiResponse(data=response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "LOCK_FAILED", "message": str(e)},
        )
