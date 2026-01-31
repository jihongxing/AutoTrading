"""
BTC 自动交易系统 — 学习路由

提供学习报告和优化建议接口。
"""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from src.api.auth import CurrentUser, CurrentAdmin, audit_log
from src.api.dependencies import LearningEngineDep
from src.api.schemas import (
    ApiResponse,
    ApproveRequest,
    LearningReportResponse,
    SuggestionListResponse,
    SuggestionResponse,
)
from src.common.utils import utc_now
from src.learning.engine import Suggestion

router = APIRouter(prefix="/learning", tags=["学习"])


@router.get("/report", response_model=ApiResponse[LearningReportResponse])
async def get_learning_report(
    user: CurrentUser,
    learning_engine: LearningEngineDep,
    period: str = "daily",
) -> ApiResponse[LearningReportResponse]:
    """
    获取学习报告
    
    返回最近的学习报告。
    """
    # 运行学习获取报告
    if period == "daily":
        report = await learning_engine.run_daily_learning()
    else:
        report = await learning_engine.run_weekly_learning()
    
    # 计算待审批数量
    pending_count = len(report.requires_approval)
    suggestions_count = (
        len(report.weight_suggestions) +
        len(report.position_suggestions) +
        len(report.stop_suggestions) +
        len(report.window_suggestions)
    )
    
    response = LearningReportResponse(
        period=report.period,
        timestamp=report.timestamp,
        start_time=report.start_time,
        end_time=report.end_time,
        total_trades=report.total_trades,
        win_rate=report.win_rate,
        avg_pnl=report.avg_pnl,
        total_pnl=report.total_pnl,
        max_drawdown=report.max_drawdown,
        sharpe_ratio=report.sharpe_ratio,
        suggestions_count=suggestions_count,
        pending_approvals=pending_count,
    )
    
    return ApiResponse(data=response)


@router.get("/suggestions", response_model=ApiResponse[SuggestionListResponse])
async def get_suggestions(
    user: CurrentUser,
    learning_engine: LearningEngineDep,
    pending_only: bool = False,
) -> ApiResponse[SuggestionListResponse]:
    """
    获取优化建议
    
    返回所有优化建议列表。
    """
    # 运行学习获取建议
    report = await learning_engine.run_daily_learning()
    
    suggestions = []
    
    # 权重建议
    for s in report.weight_suggestions:
        suggestions.append(SuggestionResponse(
            suggestion_id=str(uuid4()),
            param_name=f"weight_{s.witness_id}",
            current_value=s.current_weight,
            suggested_value=s.suggested_weight,
            action=s.action.value,
            reason=s.reason,
            confidence=s.confidence,
            requires_approval=s.requires_approval,
        ))
    
    # 仓位建议
    for s in report.position_suggestions:
        suggestions.append(SuggestionResponse(
            suggestion_id=str(uuid4()),
            param_name=s.param_name,
            current_value=s.current_value,
            suggested_value=s.suggested_value,
            action=s.action.value,
            reason=s.reason,
            confidence=s.confidence,
            requires_approval=s.requires_approval,
        ))
    
    # 止损止盈建议
    for s in report.stop_suggestions:
        suggestions.append(SuggestionResponse(
            suggestion_id=str(uuid4()),
            param_name=s.param_name,
            current_value=s.current_value,
            suggested_value=s.suggested_value,
            action=s.action.value,
            reason=s.reason,
            confidence=s.confidence,
            requires_approval=s.requires_approval,
        ))
    
    # 窗口建议
    for s in report.window_suggestions:
        suggestions.append(SuggestionResponse(
            suggestion_id=str(uuid4()),
            param_name=s.param_name,
            current_value=s.current_value,
            suggested_value=s.suggested_value,
            action=s.action.value,
            reason=s.reason,
            confidence=s.confidence,
            requires_approval=s.requires_approval,
        ))
    
    # 过滤待审批
    if pending_only:
        suggestions = [s for s in suggestions if s.requires_approval]
    
    pending_count = sum(1 for s in suggestions if s.requires_approval)
    
    response = SuggestionListResponse(
        suggestions=suggestions,
        total=len(suggestions),
        pending_count=pending_count,
    )
    
    return ApiResponse(data=response)


@router.post("/approve", response_model=ApiResponse[dict])
async def approve_suggestions(
    admin: CurrentAdmin,
    learning_engine: LearningEngineDep,
    request: ApproveRequest,
) -> ApiResponse[dict]:
    """
    审批建议
    
    需要管理员权限。批准或拒绝优化建议。
    """
    audit_log.log(
        api_key=admin.user_id,
        action="approve_suggestions",
        resource="learning",
        details={
            "suggestion_ids": request.suggestion_ids,
            "approved": request.approved,
            "comment": request.comment,
        },
    )
    
    # 简化实现：实际应根据 suggestion_id 查找并应用
    # 这里只记录审批结果
    
    result = {
        "processed": len(request.suggestion_ids),
        "approved": request.approved,
        "comment": request.comment,
        "timestamp": utc_now().isoformat(),
    }
    
    return ApiResponse(data=result)
