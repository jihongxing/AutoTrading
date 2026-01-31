"""
BTC 自动交易系统 — 协调器 API

交易协调器状态查询和控制接口。
"""

from fastapi import APIRouter, HTTPException, status

from src.api.auth import CurrentAdmin
from src.api.schemas import ApiResponse
from src.common.utils import utc_now

router = APIRouter(prefix="/coordinator", tags=["协调器"])


@router.get("/status")
async def get_coordinator_status() -> ApiResponse:
    """获取协调器状态"""
    from src.api.app import get_coordinator
    
    coordinator = get_coordinator()
    if not coordinator:
        return ApiResponse(
            data={
                "is_running": False,
                "message": "协调器未初始化",
            }
        )
    
    return ApiResponse(data=coordinator.get_status())


@router.post("/start")
async def start_coordinator(admin: CurrentAdmin) -> ApiResponse:
    """启动协调器（需要管理员权限）"""
    from src.api.app import get_coordinator
    
    coordinator = get_coordinator()
    if not coordinator:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "NOT_INITIALIZED", "message": "协调器未初始化"},
        )
    
    if coordinator.is_running:
        return ApiResponse(data={"message": "协调器已在运行"})
    
    await coordinator.start()
    return ApiResponse(data={"message": "协调器已启动"})


@router.post("/stop")
async def stop_coordinator(admin: CurrentAdmin) -> ApiResponse:
    """停止协调器（需要管理员权限）"""
    from src.api.app import get_coordinator
    
    coordinator = get_coordinator()
    if not coordinator:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "NOT_INITIALIZED", "message": "协调器未初始化"},
        )
    
    await coordinator.stop()
    return ApiResponse(data={"message": "协调器已停止"})


@router.post("/enable-trading")
async def enable_trading(admin: CurrentAdmin) -> ApiResponse:
    """启用交易（需要管理员权限）"""
    from src.api.app import get_coordinator
    
    coordinator = get_coordinator()
    if not coordinator:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "NOT_INITIALIZED", "message": "协调器未初始化"},
        )
    
    coordinator.enable_trading()
    return ApiResponse(data={"message": "交易已启用", "trading_enabled": True})


@router.post("/disable-trading")
async def disable_trading(admin: CurrentAdmin) -> ApiResponse:
    """禁用交易（需要管理员权限）"""
    from src.api.app import get_coordinator
    
    coordinator = get_coordinator()
    if not coordinator:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "NOT_INITIALIZED", "message": "协调器未初始化"},
        )
    
    coordinator.disable_trading()
    return ApiResponse(data={"message": "交易已禁用", "trading_enabled": False})


@router.get("/history")
async def get_loop_history(limit: int = 50) -> ApiResponse:
    """获取循环历史记录 - 完整决策链路"""
    from src.api.app import get_coordinator
    
    coordinator = get_coordinator()
    if not coordinator:
        return ApiResponse(data={"history": [], "total": 0})
    
    history = coordinator.loop_history
    # 返回最近的记录（倒序）
    recent = list(reversed(history[-limit:]))
    
    return ApiResponse(
        data={
            "history": [
                {
                    "loop_id": r.loop_id,
                    "timestamp": r.timestamp,
                    "step_data": r.step_data,
                    "step_witnesses": r.step_witnesses,
                    "step_aggregation": r.step_aggregation,
                    "step_risk": r.step_risk,
                    "step_state": r.step_state,
                    "step_execution": r.step_execution,
                    "final_action": r.final_action,
                    "final_reason": r.final_reason,
                    "total_duration_ms": r.total_duration_ms,
                }
                for r in recent
            ],
            "total": len(history),
        }
    )
