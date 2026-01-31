"""执行流程集成测试"""

import pytest

from src.common.enums import ClaimType, OrderSide, OrderStatus, SystemState
from src.common.models import Claim, Order
from src.core.execution.engine import ExecutionEngine
from src.core.execution.exchange import ExchangeManager
from src.core.risk.base import RiskContext
from src.core.state.service import StateMachineService
from backend.tests.mocks.exchange import MockExchangeClient


@pytest.fixture
def mock_client():
    return MockExchangeClient()


@pytest.fixture
def exchange(mock_client):
    return ExchangeManager(mock_client)


@pytest.fixture
def state_service():
    return StateMachineService()


@pytest.fixture
async def engine(exchange, state_service):
    await exchange.connect()
    return ExecutionEngine(exchange, state_service)


class TestExecutionFlowIntegration:
    """执行流程集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_execution_flow(self, engine, state_service):
        """完整执行流程"""
        # 1. 初始化
        await state_service.initialize()
        assert state_service.get_current_state() == SystemState.OBSERVING
        
        # 2. 提交 Claim
        claim = Claim(
            strategy_id="test",
            claim_type=ClaimType.MARKET_ELIGIBLE,
            confidence=0.75,
            validity_window=300,
        )
        risk_context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=500,
        )
        
        result = await state_service.submit_claim(claim, risk_context)
        assert result.success
        assert state_service.get_current_state() == SystemState.ELIGIBLE
        
        # 3. 开始交易
        await state_service.start_trading("执行交易")
        assert state_service.get_current_state() == SystemState.ACTIVE_TRADING
        
        # 4. 执行订单
        order = Order(
            order_id="test_001",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            strategy_id="test",
        )
        
        exec_result = await engine.execute_order(order)
        assert exec_result.status == OrderStatus.FILLED
        
        # 5. 完成交易
        await state_service.complete_trading("交易完成")
        assert state_service.get_current_state() == SystemState.COOLDOWN
    
    @pytest.mark.asyncio
    async def test_risk_lock_cancels_orders(self, engine, state_service):
        """风控锁定撤销订单"""
        await state_service.initialize()
        
        # 提交订单
        order = Order(
            order_id="test_002",
            side=OrderSide.BUY,
            quantity=0.1,
            strategy_id="test",
        )
        await engine.order_manager.submit_order(order)
        assert engine.order_manager.pending_count == 1
        
        # 冻结执行层
        await engine.freeze("风控触发")
        
        # 订单应该被撤销
        assert engine.order_manager.pending_count == 0
        assert engine.is_frozen
    
    @pytest.mark.asyncio
    async def test_execution_logging(self, engine, state_service):
        """执行日志记录"""
        await state_service.initialize()
        await state_service.state_machine.become_eligible("测试")
        
        order = Order(
            order_id="test_003",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            strategy_id="test",
        )
        
        await engine.execute_order(order)
        
        # 检查日志
        history = engine.logger.get_order_history(order.order_id)
        assert len(history) >= 2  # SUBMITTED + FILLED
        
        events = [e.event_type for e in history]
        assert "ORDER_SUBMITTED" in events
        assert "ORDER_FILLED" in events
