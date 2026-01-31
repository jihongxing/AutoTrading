"""
端到端交易流程测试

测试完整交易流程：
数据收集 → 证人分析 → Claim 生成 → 风控检查 → 状态机转换 → 执行
"""

import pytest
from datetime import datetime, timedelta, timezone

from src.common.enums import (
    ClaimType,
    OrderSide,
    RiskLevel,
    SystemState,
    WitnessTier,
)
from src.common.models import Claim, MarketBar
from src.core.execution import ExecutionEngine, ExchangeManager
from src.core.risk import RiskControlEngine
from src.core.risk.base import RiskContext
from src.core.state import StateMachineService
from src.learning import LearningDataCollector, LearningEngine
from src.strategy import (
    HealthManager,
    StrategyOrchestrator,
    WitnessRegistry,
    VolatilityReleaseWitness,
    RangeBreakWitness,
    TimeStructureWitness,
    RiskSentinelWitness,
)
from backend.tests.mocks.exchange import MockExchangeClient


def create_market_data(count: int = 50, trend: str = "up") -> list[MarketBar]:
    """创建测试市场数据"""
    bars = []
    price = 50000.0
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    for i in range(count):
        if trend == "up":
            change = price * 0.005
        elif trend == "down":
            change = -price * 0.005
        else:
            change = price * 0.002 * (1 if i % 2 == 0 else -1)
        
        bars.append(MarketBar(
            ts=now_ms - (count - i) * 3600000,
            interval="1h",
            open=price,
            high=price + abs(change) * 1.5,
            low=price - abs(change) * 0.5,
            close=price + change,
            volume=1000.0 + i * 10,
        ))
        price = price + change
    
    return bars


class TestEndToEndTradingFlow:
    """端到端交易流程测试"""
    
    @pytest.fixture
    def system(self):
        """初始化完整系统"""
        # 风控引擎
        risk_engine = RiskControlEngine()
        
        # 状态机服务
        state_service = StateMachineService(risk_engine)
        
        # 交易所
        mock_client = MockExchangeClient()
        exchange = ExchangeManager(mock_client)
        
        # 执行引擎
        execution_engine = ExecutionEngine(exchange, state_service, risk_engine)
        
        # 策略层
        registry = WitnessRegistry()
        health_manager = HealthManager()
        orchestrator = StrategyOrchestrator(registry, health_manager)
        
        # 注册证人
        witnesses = [
            VolatilityReleaseWitness(),
            RangeBreakWitness(),
            TimeStructureWitness(),
            RiskSentinelWitness(),
        ]
        for w in witnesses:
            registry.register(w)
            health_manager.initialize_health(w)
        
        # 学习层
        collector = LearningDataCollector()
        learning_engine = LearningEngine(collector)
        
        return {
            "risk_engine": risk_engine,
            "state_service": state_service,
            "exchange": exchange,
            "execution_engine": execution_engine,
            "registry": registry,
            "health_manager": health_manager,
            "orchestrator": orchestrator,
            "learning_engine": learning_engine,
            "mock_client": mock_client,
        }
    
    @pytest.mark.asyncio
    async def test_full_trading_cycle(self, system):
        """测试完整交易周期"""
        state_service = system["state_service"]
        orchestrator = system["orchestrator"]
        risk_engine = system["risk_engine"]
        exchange = system["exchange"]
        
        # 1. 系统初始化
        assert state_service.get_current_state() == SystemState.SYSTEM_INIT
        await state_service.initialize()
        assert state_service.get_current_state() == SystemState.OBSERVING
        
        # 2. 连接交易所
        await exchange.connect()
        assert exchange.is_connected
        
        # 3. 生成市场数据
        market_data = create_market_data(50, trend="up")
        
        # 4. 运行证人分析
        claims = await orchestrator.run_witnesses(market_data)
        
        # 5. 聚合 Claims
        result = await orchestrator.aggregate_claims(claims)
        
        # 6. 风控检查
        risk_context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=500,
        )
        risk_result = await risk_engine.check_permission(risk_context)
        assert risk_result.approved
        
        # 7. 验证系统状态
        assert state_service.is_trading_allowed() or state_service.get_current_state() == SystemState.OBSERVING
    
    @pytest.mark.asyncio
    async def test_risk_veto_flow(self, system):
        """测试风控否决流程"""
        state_service = system["state_service"]
        risk_engine = system["risk_engine"]
        
        # 初始化
        await state_service.initialize()
        
        # 触发风控否决（回撤超限）
        risk_context = RiskContext(
            equity=75000,
            initial_equity=100000,
            drawdown=0.25,  # 超过 20% 阈值
            daily_pnl=-5000,
        )
        
        risk_result = await risk_engine.check_permission(risk_context)
        
        # 验证否决
        assert not risk_result.approved
        assert risk_result.level == RiskLevel.RISK_LOCKED
    
    @pytest.mark.asyncio
    async def test_tier3_veto_flow(self, system):
        """测试 TIER 3 证人否决流程"""
        orchestrator = system["orchestrator"]
        registry = system["registry"]
        
        # 获取风控证人
        risk_sentinel = None
        for w in registry.get_veto_witnesses():
            if isinstance(w, RiskSentinelWitness):
                risk_sentinel = w
                break
        
        assert risk_sentinel is not None
        
        # 模拟连续亏损
        for _ in range(3):
            risk_sentinel.record_trade_result(is_win=False)
        
        # 运行证人
        market_data = create_market_data(50)
        claims = await orchestrator.run_witnesses(market_data)
        
        # 聚合结果
        result = await orchestrator.aggregate_claims(claims)
        
        # 验证否决
        assert not result.is_tradeable
    
    @pytest.mark.asyncio
    async def test_state_machine_transitions(self, system):
        """测试状态机转换"""
        state_service = system["state_service"]
        
        # SYSTEM_INIT → OBSERVING
        assert state_service.get_current_state() == SystemState.SYSTEM_INIT
        await state_service.initialize()
        assert state_service.get_current_state() == SystemState.OBSERVING
        
        # OBSERVING → RISK_LOCKED（强制锁定）
        await state_service.force_lock("测试锁定")
        assert state_service.get_current_state() == SystemState.RISK_LOCKED
        assert not state_service.is_trading_allowed()
        
        # RISK_LOCKED → RECOVERY
        await state_service.start_recovery("开始恢复")
        assert state_service.get_current_state() == SystemState.RECOVERY
        
        # RECOVERY → OBSERVING
        await state_service.complete_recovery()
        assert state_service.get_current_state() == SystemState.OBSERVING
    
    @pytest.mark.asyncio
    async def test_claim_to_execution_flow(self, system):
        """测试 Claim 到执行的完整流程"""
        state_service = system["state_service"]
        risk_engine = system["risk_engine"]
        orchestrator = system["orchestrator"]
        
        # 初始化
        await state_service.initialize()
        
        # 创建市场数据
        market_data = create_market_data(50, trend="up")
        
        # 运行证人
        claims = await orchestrator.run_witnesses(market_data)
        
        # 创建模拟 Claim
        test_claim = Claim(
            strategy_id="test_strategy",
            claim_type=ClaimType.MARKET_ELIGIBLE,
            confidence=0.8,
            validity_window=300,  # 5分钟有效期
            direction="long",
            constraints={"min_position": 0.01},
        )
        
        # 风控检查
        risk_context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=500,
        )
        
        # 提交 Claim 到状态机
        result = await state_service.submit_claim(test_claim, risk_context)
        
        # 验证结果
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_constitutional_principles(self, system):
        """测试宪法级原则"""
        state_service = system["state_service"]
        risk_engine = system["risk_engine"]
        orchestrator = system["orchestrator"]
        
        # 原则 1: 策略无下单权 - 策略只输出 Claim
        market_data = create_market_data(50)
        claims = await orchestrator.run_witnesses(market_data)
        
        for claim in claims:
            # Claim 只包含声明，不包含订单
            assert isinstance(claim, Claim)
            assert hasattr(claim, "claim_type")
            assert not hasattr(claim, "order")
        
        # 原则 2: 风控硬否决权
        risk_context = RiskContext(
            equity=75000,
            initial_equity=100000,
            drawdown=0.25,
            daily_pnl=-5000,
        )
        risk_result = await risk_engine.check_permission(risk_context)
        assert not risk_result.approved  # 风控否决不可反驳
        
        # 原则 3: 状态机唯一入口
        await state_service.initialize()
        # 所有交易必须经过状态机
        assert state_service.get_current_state() in [
            SystemState.OBSERVING,
            SystemState.ELIGIBLE,
            SystemState.ACTIVE_TRADING,
        ] or not state_service.is_trading_allowed()
        
        # 原则 5: 风控优先于策略
        # 即使策略发出交易信号，风控否决后也不能交易
        test_claim = Claim(
            strategy_id="test",
            claim_type=ClaimType.MARKET_ELIGIBLE,
            confidence=0.9,
            validity_window=300,  # 5分钟有效期
        )
        
        # 风控否决的上下文
        bad_context = RiskContext(
            equity=75000,
            initial_equity=100000,
            drawdown=0.25,
            daily_pnl=-5000,
        )
        
        result = await state_service.submit_claim(test_claim, bad_context)
        # 风控否决后，Claim 不会被执行
        assert result.risk_result is not None
        assert result.risk_result.approved is False

