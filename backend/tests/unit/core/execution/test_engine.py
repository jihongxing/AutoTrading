"""执行引擎测试"""

import pytest

from src.common.enums import OrderSide, OrderStatus, SystemState
from src.common.exceptions import ArchitectureViolationError, OrderRejectedError
from src.common.models import Order
from src.core.execution.engine import ExecutionEngine
from src.core.execution.exchange import ExchangeManager
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
    # 初始化状态机到 ELIGIBLE
    await state_service.initialize()
    await state_service.state_machine.become_eligible("测试")
    return ExecutionEngine(exchange, state_service)


@pytest.fixture
def test_order():
    return Order(
        order_id="test_001",
        side=OrderSide.BUY,
        quantity=0.1,
        price=50000.0,
        strategy_id="test_strategy",
    )


class TestExecutionEngine:
    """执行引擎测试"""
    
    @pytest.mark.asyncio
    async def test_execute_order_success(self, engine, test_order):
        """成功执行订单"""
        result = await engine.execute_order(test_order)
        
        assert result.status == OrderStatus.FILLED
        assert result.executed_quantity == test_order.quantity
        assert result.order_id == test_order.order_id
    
    @pytest.mark.asyncio
    async def test_idempotency(self, engine, test_order):
        """幂等性测试"""
        await engine.execute_order(test_order)
        
        with pytest.raises(OrderRejectedError):
            await engine.execute_order(test_order)
    
    @pytest.mark.asyncio
    async def test_frozen_reject(self, engine, test_order):
        """冻结状态拒绝"""
        await engine.freeze("测试冻结")
        
        from src.common.exceptions import ExecutionError
        with pytest.raises(ExecutionError):
            await engine.execute_order(test_order)
    
    @pytest.mark.asyncio
    async def test_state_machine_check(self, exchange, state_service):
        """状态机检查"""
        await exchange.connect()
        # 不初始化状态机，保持 SYSTEM_INIT
        engine = ExecutionEngine(exchange, state_service)
        
        order = Order(
            order_id="test_002",
            side=OrderSide.BUY,
            quantity=0.1,
            strategy_id="test",
        )
        
        with pytest.raises(ArchitectureViolationError):
            await engine.execute_order(order)
    
    @pytest.mark.asyncio
    async def test_cancel_order(self, engine, test_order):
        """撤销订单"""
        await engine.order_manager.submit_order(test_order)
        
        success = await engine.cancel_order(test_order.order_id, "测试撤销")
        assert success
    
    @pytest.mark.asyncio
    async def test_freeze_unfreeze(self, engine):
        """冻结和解冻"""
        assert not engine.is_frozen
        
        await engine.freeze("测试")
        assert engine.is_frozen
        
        await engine.unfreeze()
        assert not engine.is_frozen
