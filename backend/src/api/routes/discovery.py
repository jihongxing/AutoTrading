"""
BTC 自动交易系统 — 假设工厂 API 路由
"""

from fastapi import APIRouter, HTTPException

from src.common.logging import get_logger
from src.api.schemas import ApiResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _get_service():
    """获取发现服务"""
    from src.discovery.service import get_discovery_service
    return get_discovery_service()


@router.get("/status")
async def get_factory_status() -> ApiResponse:
    """获取假设工厂状态"""
    service = _get_service()
    if not service:
        return ApiResponse(data={
            "is_running": False,
            "scan_interval": 0,
            "detector_count": 0,
            "detectors": [],
            "stats": {},
            "pool_stats": {"total": 0},
        })
    return ApiResponse(data=service.get_status())


@router.get("/pool/stats")
async def get_pool_stats() -> ApiResponse:
    """获取候选池统计"""
    service = _get_service()
    if not service:
        return ApiResponse(data={"total": 0})
    return ApiResponse(data=service.pool.get_statistics())


@router.get("/pool/hypotheses")
async def list_hypotheses(status: str | None = None) -> ApiResponse:
    """列出假设"""
    service = _get_service()
    if not service:
        return ApiResponse(data=[])
    hypotheses = await service.get_hypotheses(status)
    return ApiResponse(data=hypotheses)


@router.get("/pool/hypotheses/{hypothesis_id}")
async def get_hypothesis(hypothesis_id: str) -> ApiResponse:
    """获取假设详情"""
    service = _get_service()
    if not service:
        raise HTTPException(status_code=404, detail="服务未初始化")
    hypothesis = await service.get_hypothesis(hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="假设不存在")
    return ApiResponse(data=hypothesis)


@router.post("/scan")
async def trigger_scan() -> ApiResponse:
    """触发异常扫描"""
    service = _get_service()
    if not service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    logger.info("手动触发异常扫描")
    result = await service.run_scan()
    return ApiResponse(data={
        "message": "扫描完成",
        "events_found": result.events_found,
        "hypotheses_generated": result.hypotheses_generated,
        "hypotheses_added": result.hypotheses_added,
        "duration_ms": result.duration_ms,
        "events": result.events,
        "hypotheses": result.hypotheses,
    })


@router.post("/validate/{hypothesis_id}")
async def trigger_validation(hypothesis_id: str) -> ApiResponse:
    """触发假设验证"""
    service = _get_service()
    if not service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    logger.info(f"触发假设验证: {hypothesis_id}")
    result = await service.validate_hypothesis(hypothesis_id)
    return ApiResponse(data=result)


@router.post("/promote/{hypothesis_id}")
async def promote_hypothesis(hypothesis_id: str) -> ApiResponse:
    """晋升假设为证人"""
    service = _get_service()
    if not service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    logger.info(f"晋升假设: {hypothesis_id}")
    result = await service.promote_hypothesis(hypothesis_id)
    return ApiResponse(data=result)


@router.get("/detectors")
async def list_detectors() -> ApiResponse:
    """列出所有检测器"""
    service = _get_service()
    if not service:
        return ApiResponse(data=[])
    detectors = []
    for d in service.factory._detectors:
        detectors.append({
            "detector_id": d.detector_id,
            "detector_name": d.detector_name,
        })
    return ApiResponse(data=detectors)


@router.get("/history")
async def get_scan_history(limit: int = 20) -> ApiResponse:
    """获取扫描历史"""
    service = _get_service()
    if not service:
        return ApiResponse(data=[])
    return ApiResponse(data=service.get_scan_history(limit))
