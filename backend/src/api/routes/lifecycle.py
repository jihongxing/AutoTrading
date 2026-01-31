"""
BTC 自动交易系统 — 生命周期 API

策略生命周期管理和权重管理接口。
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...common.enums import StrategyStatus
from ...common.logging import get_logger
from ...common.utils import utc_now
from ..dependencies import (
    HealthManagerDep,
    ShadowRunnerDep,
    StrategyPoolManagerDep,
    WeightManagerDep,
    WitnessRegistryDep,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/lifecycle", tags=["生命周期"])


# === 请求/响应模型 ===

class PromoteRequest(BaseModel):
    """晋升请求"""
    by: str = Field(default="admin", description="操作者")


class DemoteRequest(BaseModel):
    """降级请求"""
    by: str = Field(default="admin", description="操作者")
    reason: str = Field(default="手动降级", description="原因")


class WeightUpdateRequest(BaseModel):
    """权重更新请求"""
    base_weight: float = Field(ge=0.5, le=2.0, description="基础权重")


# === 策略状态接口 ===

@router.get("/strategies", response_model=dict[str, Any])
async def get_all_strategies(
    pool_manager: StrategyPoolManagerDep,
    registry: WitnessRegistryDep,
) -> dict[str, Any]:
    """获取所有策略状态"""
    active = pool_manager.get_all_by_status(StrategyStatus.ACTIVE)
    degraded = pool_manager.get_all_by_status(StrategyStatus.DEGRADED)
    retired = pool_manager.get_all_by_status(StrategyStatus.RETIRED)
    
    return {
        "success": True,
        "data": {
            "active": active,
            "degraded": degraded,
            "retired": retired,
            "total": len(active) + len(degraded) + len(retired),
        },
        "timestamp": utc_now().isoformat(),
    }


@router.get("/strategies/{strategy_id}", response_model=dict[str, Any])
async def get_strategy(
    strategy_id: str,
    pool_manager: StrategyPoolManagerDep,
    registry: WitnessRegistryDep,
    health_manager: HealthManagerDep,
    weight_manager: WeightManagerDep,
) -> dict[str, Any]:
    """获取单个策略详情"""
    status = pool_manager.get_status(strategy_id)
    tier = registry.get_tier(strategy_id)
    health = health_manager.get_health(strategy_id)
    weight = weight_manager.get_weight(strategy_id)
    history = pool_manager.get_state_history(strategy_id)
    
    return {
        "success": True,
        "data": {
            "strategy_id": strategy_id,
            "status": status.value if status else None,
            "tier": tier.value if tier else None,
            "health_grade": health.grade.value if health else None,
            "effective_weight": weight.effective_weight,
            "weight_detail": weight.to_dict(),
            "state_history": [r.to_dict() for r in history],
        },
        "timestamp": utc_now().isoformat(),
    }


@router.post("/strategies/{strategy_id}/promote", response_model=dict[str, Any])
async def promote_strategy(
    strategy_id: str,
    request: PromoteRequest,
    pool_manager: StrategyPoolManagerDep,
) -> dict[str, Any]:
    """手动晋升策略"""
    logger.info(f"手动晋升请求: {strategy_id}, by: {request.by}")
    
    promoted = await pool_manager.promote(strategy_id, by=request.by)
    new_status = pool_manager.get_status(strategy_id)
    
    return {
        "success": promoted,
        "data": {
            "strategy_id": strategy_id,
            "promoted": promoted,
            "new_status": new_status.value if new_status else None,
        },
        "timestamp": utc_now().isoformat(),
    }


@router.post("/strategies/{strategy_id}/demote", response_model=dict[str, Any])
async def demote_strategy(
    strategy_id: str,
    request: DemoteRequest,
    pool_manager: StrategyPoolManagerDep,
) -> dict[str, Any]:
    """手动降级策略"""
    logger.info(f"手动降级请求: {strategy_id}, by: {request.by}, reason: {request.reason}")
    
    demoted = await pool_manager.demote(strategy_id, by=request.by)
    
    return {
        "success": demoted,
        "data": {
            "strategy_id": strategy_id,
            "demoted": demoted,
            "reason": request.reason,
        },
        "timestamp": utc_now().isoformat(),
    }


@router.post("/strategies/{strategy_id}/upgrade-tier", response_model=dict[str, Any])
async def upgrade_tier(
    strategy_id: str,
    request: PromoteRequest,
    pool_manager: StrategyPoolManagerDep,
    registry: WitnessRegistryDep,
) -> dict[str, Any]:
    """升级 TIER（TIER_2 → TIER_1）"""
    logger.info(f"TIER 升级请求: {strategy_id}, by: {request.by}")
    
    upgraded = await pool_manager.upgrade_tier(strategy_id, by=request.by)
    new_tier = registry.get_tier(strategy_id)
    
    return {
        "success": upgraded,
        "data": {
            "strategy_id": strategy_id,
            "upgraded": upgraded,
            "new_tier": new_tier.value if new_tier else None,
        },
        "timestamp": utc_now().isoformat(),
    }


@router.post("/strategies/{strategy_id}/retire", response_model=dict[str, Any])
async def retire_strategy(
    strategy_id: str,
    request: DemoteRequest,
    pool_manager: StrategyPoolManagerDep,
) -> dict[str, Any]:
    """废弃策略"""
    logger.info(f"废弃请求: {strategy_id}, by: {request.by}")
    
    retired = await pool_manager.retire(strategy_id, by=request.by)
    
    return {
        "success": retired,
        "data": {
            "strategy_id": strategy_id,
            "retired": retired,
        },
        "timestamp": utc_now().isoformat(),
    }


# === 权重接口 ===

@router.get("/weights", response_model=dict[str, Any])
async def get_all_weights(
    weight_manager: WeightManagerDep,
) -> dict[str, Any]:
    """获取所有权重"""
    weights = weight_manager.get_all_weights()
    
    return {
        "success": True,
        "data": {
            "weights": [w.to_dict() for w in weights],
            "total": len(weights),
        },
        "timestamp": utc_now().isoformat(),
    }


@router.get("/weights/{strategy_id}", response_model=dict[str, Any])
async def get_weight(
    strategy_id: str,
    weight_manager: WeightManagerDep,
) -> dict[str, Any]:
    """获取单个权重"""
    weight = weight_manager.get_weight(strategy_id)
    
    return {
        "success": True,
        "data": weight.to_dict(),
        "timestamp": utc_now().isoformat(),
    }


@router.put("/weights/{strategy_id}", response_model=dict[str, Any])
async def update_weight(
    strategy_id: str,
    request: WeightUpdateRequest,
    weight_manager: WeightManagerDep,
) -> dict[str, Any]:
    """修改基础权重（L1 配置级别）"""
    logger.info(f"权重更新请求: {strategy_id}, base_weight: {request.base_weight}")
    
    weight_manager.set_base_weight(strategy_id, request.base_weight)
    updated_weight = weight_manager.get_weight(strategy_id)
    
    return {
        "success": True,
        "data": updated_weight.to_dict(),
        "timestamp": utc_now().isoformat(),
    }


# === 影子运行接口 ===

@router.get("/shadow", response_model=dict[str, Any])
async def get_shadow_strategies(
    shadow_runner: ShadowRunnerDep,
) -> dict[str, Any]:
    """获取所有影子运行中的策略"""
    performances = shadow_runner.get_all_performances()
    
    return {
        "success": True,
        "data": {
            "strategies": [p.to_dict() for p in performances],
            "total": shadow_runner.strategy_count,
        },
        "timestamp": utc_now().isoformat(),
    }


@router.get("/shadow/{strategy_id}/performance", response_model=dict[str, Any])
async def get_shadow_performance(
    strategy_id: str,
    shadow_runner: ShadowRunnerDep,
) -> dict[str, Any]:
    """获取影子运行绩效"""
    perf = shadow_runner.get_performance(strategy_id)
    
    if not perf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"影子策略不存在: {strategy_id}",
        )
    
    return {
        "success": True,
        "data": perf.to_dict(),
        "timestamp": utc_now().isoformat(),
    }


@router.get("/shadow/{strategy_id}/records", response_model=dict[str, Any])
async def get_shadow_records(
    strategy_id: str,
    shadow_runner: ShadowRunnerDep,
) -> dict[str, Any]:
    """获取影子交易记录"""
    records = shadow_runner.get_records(strategy_id)
    
    return {
        "success": True,
        "data": {
            "strategy_id": strategy_id,
            "records": [r.to_dict() for r in records],
            "total": len(records),
        },
        "timestamp": utc_now().isoformat(),
    }
