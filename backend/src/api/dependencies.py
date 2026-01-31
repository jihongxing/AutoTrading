"""
BTC 自动交易系统 — API 依赖注入

提供各模块服务的依赖注入。
"""

from typing import Annotated

from fastapi import Depends

from src.common.logging import get_logger
from src.core.execution import ExecutionEngine
from src.core.risk import RiskEngine
from src.core.state import StateService
from src.data import DataAPI
from src.discovery.pool.manager import HypothesisPoolManager
from src.learning import LearningEngine, LearningDataCollector
from src.strategy import HealthManager, StrategyOrchestrator, WitnessRegistry
from src.strategy.lifecycle import StrategyPoolManager, WeightManager, ShadowRunner

logger = get_logger(__name__)


# ========================================
# 单例实例（生产环境应使用更完善的 DI 容器）
# ========================================

_state_service: StateService | None = None
_risk_engine: RiskEngine | None = None
_execution_engine: ExecutionEngine | None = None
_data_api: DataAPI | None = None
_witness_registry: WitnessRegistry | None = None
_health_manager: HealthManager | None = None
_strategy_orchestrator: StrategyOrchestrator | None = None
_learning_engine: LearningEngine | None = None

# 生命周期管理
_hypothesis_pool: HypothesisPoolManager | None = None
_weight_manager: WeightManager | None = None
_strategy_pool_manager: StrategyPoolManager | None = None
_shadow_runner: ShadowRunner | None = None


def init_services(
    state_service: StateService | None = None,
    risk_engine: RiskEngine | None = None,
    execution_engine: ExecutionEngine | None = None,
    data_api: DataAPI | None = None,
    witness_registry: WitnessRegistry | None = None,
    health_manager: HealthManager | None = None,
    learning_engine: LearningEngine | None = None,
    hypothesis_pool: HypothesisPoolManager | None = None,
    weight_manager: WeightManager | None = None,
    strategy_pool_manager: StrategyPoolManager | None = None,
    shadow_runner: ShadowRunner | None = None,
) -> None:
    """
    初始化服务实例
    
    在应用启动时调用，注入实际的服务实例。
    """
    global _state_service, _risk_engine, _execution_engine, _data_api
    global _witness_registry, _health_manager, _strategy_orchestrator, _learning_engine
    global _hypothesis_pool, _weight_manager, _strategy_pool_manager, _shadow_runner
    
    _state_service = state_service
    _risk_engine = risk_engine
    _execution_engine = execution_engine
    _data_api = data_api
    _witness_registry = witness_registry
    _health_manager = health_manager
    _learning_engine = learning_engine
    _hypothesis_pool = hypothesis_pool
    _weight_manager = weight_manager
    _strategy_pool_manager = strategy_pool_manager
    _shadow_runner = shadow_runner
    
    if _witness_registry and _health_manager:
        _strategy_orchestrator = StrategyOrchestrator(_witness_registry, _health_manager, _weight_manager)
    
    logger.info("API 服务依赖已初始化")


# ========================================
# 依赖函数
# ========================================

async def get_state_service() -> StateService:
    """获取状态机服务"""
    if _state_service is None:
        # 返回默认实例用于测试
        return StateService()
    return _state_service


async def get_risk_engine() -> RiskEngine:
    """获取风控引擎"""
    if _risk_engine is None:
        return RiskEngine()
    return _risk_engine


async def get_execution_engine() -> ExecutionEngine:
    """获取执行引擎"""
    if _execution_engine is None:
        # 返回 None，让路由处理
        raise RuntimeError("ExecutionEngine 未初始化")
    return _execution_engine


async def get_data_api() -> DataAPI:
    """获取数据 API"""
    global _data_api
    if _data_api is None:
        try:
            from src.data import QuestDBStorage, DataAccessRole
            from src.data.api import DataAPI
            storage = QuestDBStorage()
            _data_api = DataAPI(storage, DataAccessRole.STRATEGY)
        except Exception:
            # 数据库不可用时返回 None
            return None
    return _data_api


async def get_witness_registry() -> WitnessRegistry:
    """获取证人注册表"""
    if _witness_registry is None:
        return WitnessRegistry()
    return _witness_registry


async def get_health_manager() -> HealthManager:
    """获取健康度管理器"""
    if _health_manager is None:
        return HealthManager()
    return _health_manager


async def get_strategy_orchestrator() -> StrategyOrchestrator:
    """获取策略编排器"""
    if _strategy_orchestrator is None:
        registry = await get_witness_registry()
        health = await get_health_manager()
        return StrategyOrchestrator(registry, health)
    return _strategy_orchestrator


async def get_learning_engine() -> LearningEngine:
    """获取学习引擎"""
    if _learning_engine is None:
        collector = LearningDataCollector()
        return LearningEngine(collector)
    return _learning_engine


async def get_hypothesis_pool() -> HypothesisPoolManager:
    """获取假设候选池"""
    if _hypothesis_pool is None:
        return HypothesisPoolManager()
    return _hypothesis_pool


async def get_weight_manager() -> WeightManager:
    """获取权重管理器"""
    if _weight_manager is None:
        health = await get_health_manager()
        return WeightManager(health_manager=health, config_path="config/strategy.yaml")
    return _weight_manager


async def get_strategy_pool_manager() -> StrategyPoolManager:
    """获取策略池管理器"""
    if _strategy_pool_manager is None:
        pool = await get_hypothesis_pool()
        registry = await get_witness_registry()
        health = await get_health_manager()
        weight = await get_weight_manager()
        return StrategyPoolManager(pool, registry, health, weight)
    return _strategy_pool_manager


async def get_shadow_runner() -> ShadowRunner:
    """获取影子运行器"""
    if _shadow_runner is None:
        return ShadowRunner()
    return _shadow_runner


# ========================================
# 类型别名
# ========================================

StateServiceDep = Annotated[StateService, Depends(get_state_service)]
RiskEngineDep = Annotated[RiskEngine, Depends(get_risk_engine)]
ExecutionEngineDep = Annotated[ExecutionEngine, Depends(get_execution_engine)]
DataAPIDep = Annotated[DataAPI | None, Depends(get_data_api)]
WitnessRegistryDep = Annotated[WitnessRegistry, Depends(get_witness_registry)]
HealthManagerDep = Annotated[HealthManager, Depends(get_health_manager)]
StrategyOrchestratorDep = Annotated[StrategyOrchestrator, Depends(get_strategy_orchestrator)]
LearningEngineDep = Annotated[LearningEngine, Depends(get_learning_engine)]
HypothesisPoolDep = Annotated[HypothesisPoolManager, Depends(get_hypothesis_pool)]
WeightManagerDep = Annotated[WeightManager, Depends(get_weight_manager)]
StrategyPoolManagerDep = Annotated[StrategyPoolManager, Depends(get_strategy_pool_manager)]
ShadowRunnerDep = Annotated[ShadowRunner, Depends(get_shadow_runner)]
