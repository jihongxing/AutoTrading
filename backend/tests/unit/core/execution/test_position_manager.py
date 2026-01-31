"""仓位管理器测试"""

import pytest

from src.common.enums import OrderSide
from src.common.models import Order
from src.core.execution.exchange import ExchangeManager, Position
from src.core.execution.position_manager import PositionManager
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
    return PositionManager(exchange)


class TestPositionManager:
    """仓位管理器测试"""
    
    @pytest.mark.asyncio
    async def test_get_position(self, manager):
        """获取仓位"""
        position = await manager.get_current_position()
        
        assert position.symbol == "BTCUSDT"
        assert position.side == "NONE"
    
    @pytest.mark.asyncio
    async def test_get_balance(self, manager):
        """获取余额"""
        balance = await manager.get_balance()
        
        assert balance == 100000.0
    
    @pytest.mark.asyncio
    async def test_check_position_limit_pass(self, manager):
        """仓位限制检查通过"""
        order = Order(
            order_id="test",
            side=OrderSide.BUY,
            quantity=0.01,
            price=50000.0,
            strategy_id="test",
        )
        
        passed, reason = await manager.check_position_limit(order)
        
        assert passed
    
    @pytest.mark.asyncio
    async def test_check_position_limit_exceed_single(self, manager):
        """单笔仓位超限"""
        order = Order(
            order_id="test",
            side=OrderSide.BUY,
            quantity=1.0,  # 50000 USDT = 50%
            price=50000.0,
            strategy_id="test",
        )
        
        passed, reason = await manager.check_position_limit(order)
        
        assert not passed
        assert "单笔" in reason
    
    @pytest.mark.asyncio
    async def test_sync_position(self, manager):
        """同步仓位"""
        snapshot = await manager.sync_position()
        
        assert snapshot.position is not None
        assert snapshot.balance == 100000.0
    
    @pytest.mark.asyncio
    async def test_position_ratio(self, manager, mock_client):
        """仓位占比"""
        mock_client.set_position(Position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=0.1,
            entry_price=50000.0,
        ))
        
        await manager.sync_position()
        ratio = manager.get_position_ratio()
        
        assert ratio == 0.05  # 5000 / 100000
