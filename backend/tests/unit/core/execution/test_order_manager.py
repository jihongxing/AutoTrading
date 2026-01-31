"""订单管理器测试"""

import pytest

from src.common.enums import OrderSide, OrderStatus
from src.common.models import Order
from src.core.execution.exchange import ExchangeManager
from src.core.execution.order_manager import OrderManager
from backend.tests.mocks.exchange import MockExchangeClient


@pytest.fixture
def mock_client():
    return MockExchangeClient()


@pytest.fixture
def exchange(mock_client):
    return ExchangeManager(mock_client)


@pytest.fixture
async def manager(exchange):
    await exchange.connect()
    return OrderManager(exchange)


@pytest.fixture
def test_order():
    return Order(
        order_id="test_001",
        side=OrderSide.BUY,
        quantity=0.1,
        strategy_id="test",
    )


class TestOrderManager:
    """订单管理器测试"""
    
    @pytest.mark.asyncio
    async def test_submit_order(self, manager, test_order):
        """提交订单"""
        order_id = await manager.submit_order(test_order)
        
        assert order_id == test_order.order_id
        assert manager.pending_count == 1
    
    @pytest.mark.asyncio
    async def test_duplicate_order(self, manager, test_order):
        """重复订单"""
        await manager.submit_order(test_order)
        order_id = await manager.submit_order(test_order)
        
        assert order_id == test_order.order_id
        assert manager.pending_count == 1  # 不重复添加
    
    @pytest.mark.asyncio
    async def test_cancel_order(self, manager, test_order):
        """撤销订单"""
        await manager.submit_order(test_order)
        
        success = await manager.cancel_order(test_order.order_id, "测试")
        
        assert success
        assert manager.pending_count == 0
    
    @pytest.mark.asyncio
    async def test_cancel_all(self, manager):
        """批量撤销"""
        for i in range(3):
            order = Order(
                order_id=f"test_{i}",
                side=OrderSide.BUY,
                quantity=0.1,
                strategy_id="test",
            )
            await manager.submit_order(order)
        
        assert manager.pending_count == 3
        
        cancelled = await manager.cancel_all_pending("测试")
        
        assert cancelled == 3
        assert manager.pending_count == 0
    
    @pytest.mark.asyncio
    async def test_get_pending_orders(self, manager, test_order):
        """获取待处理订单"""
        await manager.submit_order(test_order)
        
        pending = manager.get_pending_orders()
        
        assert len(pending) == 1
        assert pending[0].order_id == test_order.order_id
    
    @pytest.mark.asyncio
    async def test_mark_completed(self, manager, test_order):
        """标记完成"""
        await manager.submit_order(test_order)
        await manager.mark_completed(test_order.order_id, OrderStatus.FILLED)
        
        assert manager.pending_count == 0
