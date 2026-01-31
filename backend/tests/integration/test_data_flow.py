"""数据流集成测试"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.common.models import MarketBar, RiskEvent
from src.common.enums import RiskEventType, RiskLevel
from src.data.api import (
    create_collector_api,
    create_risk_api,
    create_strategy_api,
)
from src.data.storage import QuestDBStorage


@pytest.fixture
def mock_storage():
    """模拟存储"""
    storage = MagicMock(spec=QuestDBStorage)
    storage.write_bars = AsyncMock(return_value=1)
    storage.write_risk_event = AsyncMock()
    storage.query_bars = AsyncMock(return_value=[
        {
            "ts": 1704067200000000,
            "symbol": "BTCUSDT",
            "interval": "1h",
            "open": 42000.0,
            "high": 42500.0,
            "low": 41800.0,
            "close": 42300.0,
            "volume": 1000.0,
            "quote_volume": 42000000.0,
            "trades": 100,
        }
    ])
    return storage


class TestDataFlowIntegration:
    """数据流集成测试"""
    
    @pytest.mark.asyncio
    async def test_collector_writes_strategy_reads(self, mock_storage):
        """测试采集器写入，策略层读取"""
        # 采集器写入
        collector_api = create_collector_api(mock_storage)
        bars = [
            MarketBar(
                ts=1704067200000,
                interval="1h",
                open=42000.0,
                high=42500.0,
                low=41800.0,
                close=42300.0,
                volume=1000.0,
            )
        ]
        await collector_api.write_bars(bars)
        
        # 策略层读取
        strategy_api = create_strategy_api(mock_storage)
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        result = await strategy_api.get_bars("BTCUSDT", "1h", start, end)
        
        assert len(result) == 1
        assert result[0].close == 42300.0
    
    @pytest.mark.asyncio
    async def test_risk_writes_event(self, mock_storage):
        """测试风控层写入事件"""
        risk_api = create_risk_api(mock_storage)
        
        event = RiskEvent(
            event_id="e1",
            event_type=RiskEventType.DRAWDOWN_EXCEEDED,
            level=RiskLevel.WARNING,
            description="回撤接近阈值",
            value=0.18,
            threshold=0.20,
        )
        
        await risk_api.write_risk_event(event)
        mock_storage.write_risk_event.assert_called_once_with(event)
    
    @pytest.mark.asyncio
    async def test_role_isolation(self, mock_storage):
        """测试角色隔离"""
        from src.common.exceptions import ArchitectureViolationError
        
        strategy_api = create_strategy_api(mock_storage)
        collector_api = create_collector_api(mock_storage)
        
        # 策略层不能写
        with pytest.raises(ArchitectureViolationError):
            await strategy_api.write_bars([])
        
        # 采集层不能读
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        with pytest.raises(ArchitectureViolationError):
            await collector_api.get_bars("BTCUSDT", "1h", start, end)
