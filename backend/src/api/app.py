"""
BTC 自动交易系统 — FastAPI 应用

主应用入口，配置中间件、异常处理和路由。
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

# 加载环境变量（必须在其他导入之前）
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..common.logging import get_logger
from ..common.utils import utc_now

from .routes import (
    admin_router,
    auth_router,
    coordinator_router,
    data_router,
    discovery_router,
    execution_router,
    learning_router,
    lifecycle_router,
    risk_router,
    state_router,
    strategy_router,
    user_router,
)
from .websocket import ws_manager, ws_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("API 服务启动")
    
    # 初始化证人注册表
    _init_witnesses()
    
    # 初始化状态机
    await _init_state_machine()
    
    # 初始化交易协调器
    await _init_coordinator()
    
    # 初始化发现服务
    await _init_discovery_service()
    
    # 启动 WebSocket 心跳
    await ws_manager.start_heartbeat(interval=30)
    yield
    # 停止发现服务
    await _stop_discovery_service()
    # 停止交易协调器
    await _stop_coordinator()
    # 停止 WebSocket 心跳
    await ws_manager.stop_heartbeat()
    await ws_manager.disconnect_all()
    logger.info("API 服务关闭")


async def _init_state_machine():
    """初始化状态机，从 SYSTEM_INIT 转到 OBSERVING"""
    from . import dependencies
    from src.core.state import StateService
    
    try:
        # 如果未初始化，创建默认实例并直接赋值（不调用 init_services 避免覆盖）
        if dependencies._state_service is None:
            dependencies._state_service = StateService()
        
        state_service = dependencies._state_service
        if state_service.get_current_state().value == "system_init":
            await state_service.initialize()
            logger.info("状态机初始化完成，进入 OBSERVING 状态")
    except Exception as e:
        logger.error(f"状态机初始化失败: {e}")


# 全局协调器实例
_coordinator = None


async def _init_coordinator():
    """初始化交易协调器"""
    global _coordinator
    from . import dependencies
    from src.core.coordinator import TradingCoordinator, CoordinatorConfig
    from src.core.execution.exchange.binance import BinanceClient
    from src.core.execution.engine import ExecutionEngine
    
    try:
        # 获取依赖
        state_service = dependencies._state_service
        orchestrator = dependencies._strategy_orchestrator
        
        logger.info(f"协调器初始化检查: state_service={state_service is not None}, orchestrator={orchestrator is not None}")
        
        if not state_service or not orchestrator:
            logger.warning(f"状态服务或编排器未初始化，跳过协调器启动 (state={state_service}, orch={orchestrator})")
            return
        
        # 创建 Binance 客户端（使用 testnet）
        import os
        api_key = os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET", "")
        testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        
        binance_client = None
        execution_engine = None
        
        if api_key and api_secret:
            try:
                binance_client = BinanceClient(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=testnet,
                )
                await binance_client.connect()
                
                # 测试连接：获取一条K线数据
                test_bars = await binance_client.get_klines(
                    symbol="BTCUSDT",
                    interval="1m",
                    limit=1,
                )
                if test_bars:
                    logger.info(f"Binance 客户端已连接并验证 (testnet={testnet}), 当前价格: {test_bars[0].close}")
                else:
                    logger.warning(f"Binance 客户端已连接但无法获取数据 (testnet={testnet})")
                
                # 创建执行引擎
                execution_engine = ExecutionEngine(
                    exchange=binance_client,
                    state_service=state_service,
                )
                dependencies._execution_engine = execution_engine
            except Exception as e:
                logger.error(f"Binance 客户端连接失败: {e}")
                binance_client = None
                execution_engine = None
        else:
            logger.warning("未配置 Binance API Key，协调器将无法获取实时数据")
        
        # 创建协调器（默认禁用交易，只观察）
        config = CoordinatorConfig(
            loop_interval=60,
            trading_enabled=False,  # 默认禁用，需要手动启用
        )
        
        _coordinator = TradingCoordinator(
            state_service=state_service,
            orchestrator=orchestrator,
            risk_engine=dependencies._risk_engine or __import__('src.core.risk', fromlist=['RiskEngine']).RiskEngine(),
            execution_engine=execution_engine,
            data_api=dependencies._data_api,
            config=config,
        )
        
        # 启动协调器
        await _coordinator.start()
        logger.info("交易协调器已启动（观察模式）")
        
    except Exception as e:
        logger.error(f"协调器初始化失败: {e}")


async def _stop_coordinator():
    """停止交易协调器"""
    global _coordinator
    if _coordinator:
        await _coordinator.stop()
        _coordinator = None


# 全局发现服务实例
_discovery_service = None


async def _init_discovery_service():
    """初始化发现服务"""
    global _coordinator, _discovery_service
    from src.discovery.service import init_discovery_service
    
    try:
        # 创建发现服务（每小时扫描一次）
        _discovery_service = init_discovery_service(scan_interval=3600)
        
        # 设置数据获取器（使用协调器的 Binance 客户端）
        if _coordinator and _coordinator._binance_client:
            _discovery_service.set_data_fetcher(_coordinator._binance_client)
            logger.info("发现服务已配置数据源")
        
        # 启动发现服务
        await _discovery_service.start()
        logger.info("发现服务已启动")
        
        # 立即运行一次扫描
        result = await _discovery_service.run_scan()
        logger.info(f"初始扫描完成: 事件={result.events_found}, 假设={result.hypotheses_added}")
        
    except Exception as e:
        logger.error(f"发现服务初始化失败: {e}")


async def _stop_discovery_service():
    """停止发现服务"""
    global _discovery_service
    if _discovery_service:
        await _discovery_service.stop()
        _discovery_service = None


def get_coordinator():
    """获取协调器实例"""
    return _coordinator


def _init_witnesses():
    """初始化证人注册表"""
    from .dependencies import init_services
    from src.strategy import WitnessRegistry, HealthManager
    from src.strategy.witnesses import (
        LiquiditySweepWitness,
        MacroSentinelWitness,
        MicrostructureWitness,
        RangeBreakWitness,
        RiskSentinelWitness,
        TimeStructureWitness,
        VolatilityAsymmetryWitness,
        VolatilityReleaseWitness,
    )
    
    registry = WitnessRegistry()
    health_manager = HealthManager()
    
    # 注册所有证人
    witnesses = [
        LiquiditySweepWitness(),
        MacroSentinelWitness(),
        MicrostructureWitness(),
        RangeBreakWitness(),
        RiskSentinelWitness(),
        TimeStructureWitness(),
        VolatilityAsymmetryWitness(),
        VolatilityReleaseWitness(),
    ]
    
    for witness in witnesses:
        registry.register(witness)
        # 初始化证人健康度
        health_manager.initialize_health(witness)
    
    # 注入到依赖系统
    init_services(
        witness_registry=registry,
        health_manager=health_manager,
    )
    
    logger.info(f"已注册 {registry.count} 个证人，健康度已初始化")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用
    
    Returns:
        配置好的 FastAPI 实例
    """
    app = FastAPI(
        title="BTC 自动交易系统 API",
        description="BTC 自动交易系统的 REST API 接口",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册异常处理器
    register_exception_handlers(app)
    
    # 注册路由
    register_routes(app)
    
    return app


def register_exception_handlers(app: FastAPI) -> None:
    """注册异常处理器"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """HTTP 异常处理"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "error": exc.detail if isinstance(exc.detail, dict) else {
                    "code": "HTTP_ERROR",
                    "message": str(exc.detail),
                },
                "timestamp": utc_now().isoformat(),
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """通用异常处理"""
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误",
                },
                "timestamp": utc_now().isoformat(),
            },
        )


def register_routes(app: FastAPI) -> None:
    """注册路由"""
    api_prefix = "/api/v1"
    
    # 核心业务路由
    app.include_router(state_router, prefix=api_prefix)
    app.include_router(strategy_router, prefix=api_prefix)
    app.include_router(risk_router, prefix=api_prefix)
    app.include_router(execution_router, prefix=api_prefix)
    app.include_router(data_router, prefix=api_prefix)
    app.include_router(learning_router, prefix=api_prefix)
    app.include_router(discovery_router, prefix=api_prefix)
    app.include_router(lifecycle_router, prefix=api_prefix)
    app.include_router(coordinator_router, prefix=api_prefix)
    
    # 用户认证路由（无前缀）
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(admin_router)
    
    # WebSocket 路由
    app.include_router(ws_router)
    
    # 健康检查端点
    @app.get("/health", tags=["系统"])
    async def health_check() -> dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "timestamp": utc_now().isoformat(),
            "version": "1.0.0",
            "websocket": ws_manager.get_stats(),
        }
    
    @app.get("/", tags=["系统"])
    async def root() -> dict[str, Any]:
        """根路径"""
        return {
            "name": "BTC 自动交易系统 API",
            "version": "1.0.0",
            "docs": "/docs",
        }


# 创建应用实例
app = create_app()
