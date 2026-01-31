"""
BTC 自动交易系统 — REST API 模块

提供系统对外的 REST API 接口：
- 系统状态查询和管理
- 证人管理
- 风控状态和事件
- 订单和仓位管理
- 市场数据查询
- 学习报告和建议审批
"""

from .app import app, create_app
from .auth import ApiKey, Permission, audit_log, require_permission, verify_api_key
from .dependencies import (
    DataAPIDep,
    ExecutionEngineDep,
    HealthManagerDep,
    LearningEngineDep,
    RiskEngineDep,
    StateServiceDep,
    StrategyOrchestratorDep,
    WitnessRegistryDep,
    init_services,
)
from .schemas import (
    ApiResponse,
    ErrorDetail,
    LearningReportResponse,
    OrderListResponse,
    OrderResponse,
    PositionListResponse,
    PositionResponse,
    RiskEventResponse,
    RiskStatusResponse,
    StateHistoryResponse,
    StateResponse,
    SuggestionListResponse,
    SuggestionResponse,
    WitnessHealthResponse,
    WitnessListResponse,
    WitnessResponse,
)

__all__ = [
    # 应用
    "app",
    "create_app",
    # 认证
    "ApiKey",
    "Permission",
    "verify_api_key",
    "require_permission",
    "audit_log",
    # 依赖
    "init_services",
    "StateServiceDep",
    "RiskEngineDep",
    "ExecutionEngineDep",
    "DataAPIDep",
    "WitnessRegistryDep",
    "HealthManagerDep",
    "StrategyOrchestratorDep",
    "LearningEngineDep",
    # 响应模型
    "ApiResponse",
    "ErrorDetail",
    "StateResponse",
    "StateHistoryResponse",
    "WitnessResponse",
    "WitnessListResponse",
    "WitnessHealthResponse",
    "RiskStatusResponse",
    "RiskEventResponse",
    "OrderResponse",
    "OrderListResponse",
    "PositionResponse",
    "PositionListResponse",
    "LearningReportResponse",
    "SuggestionResponse",
    "SuggestionListResponse",
]
