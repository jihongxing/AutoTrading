"""
BTC 自动交易系统 — 策略路由

提供证人管理接口。
"""

from fastapi import APIRouter, HTTPException, status

from src.api.auth import CurrentUser, CurrentAdmin, audit_log
from src.api.dependencies import HealthManagerDep, WitnessRegistryDep
from src.api.schemas import (
    ApiResponse,
    WitnessHealthResponse,
    WitnessListResponse,
    WitnessResponse,
)
from src.common.enums import HealthGrade, WitnessStatus

router = APIRouter(prefix="/witnesses", tags=["策略/证人"])


@router.get("", response_model=ApiResponse[WitnessListResponse])
async def get_all_witnesses(
    user: CurrentUser,
    registry: WitnessRegistryDep,
    health_manager: HealthManagerDep,
) -> ApiResponse[WitnessListResponse]:
    """
    获取所有证人
    
    返回所有注册的证人列表及其状态。
    """
    witnesses = registry.get_all_witnesses()
    
    witness_responses = []
    for w in witnesses:
        health = health_manager.get_health(w.strategy_id)
        health_response = None
        if health:
            health_response = WitnessHealthResponse(
                witness_id=health.witness_id,
                tier=health.tier,
                status=health.status,
                grade=health.grade,
                win_rate=health.win_rate,
                sample_count=health.sample_count,
                weight=health.weight,
            )
        
        witness_responses.append(WitnessResponse(
            witness_id=w.strategy_id,
            tier=w.tier,
            status=WitnessStatus.ACTIVE if w.is_active else WitnessStatus.MUTED,
            is_active=w.is_active,
            validity_window=w.validity_window,
            health=health_response,
        ))
    
    response = WitnessListResponse(
        witnesses=witness_responses,
        total=len(witness_responses),
        active_count=registry.active_count,
    )
    
    return ApiResponse(data=response)


@router.get("/{witness_id}", response_model=ApiResponse[WitnessResponse])
async def get_witness(
    witness_id: str,
    user: CurrentUser,
    registry: WitnessRegistryDep,
    health_manager: HealthManagerDep,
) -> ApiResponse[WitnessResponse]:
    """
    获取证人详情
    
    返回指定证人的详细信息。
    """
    witness = registry.get_witness(witness_id)
    
    if not witness:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WITNESS_NOT_FOUND", "message": f"证人不存在: {witness_id}"},
        )
    
    health = health_manager.get_health(witness_id)
    health_response = None
    if health:
        health_response = WitnessHealthResponse(
            witness_id=health.witness_id,
            tier=health.tier,
            status=health.status,
            grade=health.grade,
            win_rate=health.win_rate,
            sample_count=health.sample_count,
            weight=health.weight,
        )
    
    response = WitnessResponse(
        witness_id=witness.strategy_id,
        tier=witness.tier,
        status=WitnessStatus.ACTIVE if witness.is_active else WitnessStatus.MUTED,
        is_active=witness.is_active,
        validity_window=witness.validity_window,
        health=health_response,
    )
    
    return ApiResponse(data=response)


@router.get("/{witness_id}/health", response_model=ApiResponse[WitnessHealthResponse])
async def get_witness_health(
    witness_id: str,
    user: CurrentUser,
    health_manager: HealthManagerDep,
) -> ApiResponse[WitnessHealthResponse]:
    """
    获取证人健康度
    
    返回指定证人的健康度信息。
    """
    health = health_manager.get_health(witness_id)
    
    if not health:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "HEALTH_NOT_FOUND", "message": f"证人健康度不存在: {witness_id}"},
        )
    
    response = WitnessHealthResponse(
        witness_id=health.witness_id,
        tier=health.tier,
        status=health.status,
        grade=health.grade,
        win_rate=health.win_rate,
        sample_count=health.sample_count,
        weight=health.weight,
    )
    
    return ApiResponse(data=response)


@router.post("/{witness_id}/mute", response_model=ApiResponse[WitnessResponse])
async def mute_witness(
    witness_id: str,
    user: CurrentUser,
    registry: WitnessRegistryDep,
) -> ApiResponse[WitnessResponse]:
    """
    静默证人
    
    将指定证人设置为静默状态，不再参与信号生成。
    """
    witness = registry.get_witness(witness_id)
    
    if not witness:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WITNESS_NOT_FOUND", "message": f"证人不存在: {witness_id}"},
        )
    
    audit_log.log(
        api_key=user.user_id,
        action="mute_witness",
        resource=witness_id,
    )
    
    witness.mute()
    
    response = WitnessResponse(
        witness_id=witness.strategy_id,
        tier=witness.tier,
        status=WitnessStatus.MUTED,
        is_active=False,
        validity_window=witness.validity_window,
    )
    
    return ApiResponse(data=response)


@router.post("/{witness_id}/activate", response_model=ApiResponse[WitnessResponse])
async def activate_witness(
    witness_id: str,
    user: CurrentUser,
    registry: WitnessRegistryDep,
) -> ApiResponse[WitnessResponse]:
    """
    激活证人
    
    将指定证人设置为激活状态。
    """
    witness = registry.get_witness(witness_id)
    
    if not witness:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WITNESS_NOT_FOUND", "message": f"证人不存在: {witness_id}"},
        )
    
    audit_log.log(
        api_key=user.user_id,
        action="activate_witness",
        resource=witness_id,
    )
    
    witness.activate()
    
    response = WitnessResponse(
        witness_id=witness.strategy_id,
        tier=witness.tier,
        status=WitnessStatus.ACTIVE,
        is_active=True,
        validity_window=witness.validity_window,
    )
    
    return ApiResponse(data=response)
