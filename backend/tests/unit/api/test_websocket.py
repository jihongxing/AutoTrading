"""
WebSocket 模块单元测试
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.websocket.manager import (
    Connection,
    ConnectionManager,
    WSAction,
    WSChannel,
    WSMessage,
)
from src.api.websocket.publisher import WSPublisher


class TestWSMessage:
    """WSMessage 测试"""
    
    def test_to_json(self):
        """测试 JSON 序列化"""
        message = WSMessage(
            channel=WSChannel.TRADING,
            type="position",
            action=WSAction.UPDATE,
            data={"symbol": "BTCUSDT", "quantity": 0.5},
        )
        
        result = json.loads(message.to_json())
        
        assert result["channel"] == "trading"
        assert result["type"] == "position"
        assert result["action"] == "update"
        assert result["data"]["symbol"] == "BTCUSDT"
        assert "timestamp" in result


class TestConnectionManager:
    """ConnectionManager 测试"""
    
    @pytest.fixture
    def manager(self):
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """测试建立连接"""
        connection = await manager.connect(
            websocket=mock_websocket,
            user_id="user-001",
            channels=[WSChannel.TRADING],
        )
        
        assert connection.user_id == "user-001"
        assert WSChannel.TRADING in connection.channels
        assert manager.connection_count == 1
        assert manager.is_connected("user-001")
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """测试断开连接"""
        await manager.connect(
            websocket=mock_websocket,
            user_id="user-001",
            channels=[WSChannel.TRADING],
        )
        
        await manager.disconnect("user-001")
        
        assert manager.connection_count == 0
        assert not manager.is_connected("user-001")
    
    @pytest.mark.asyncio
    async def test_subscribe(self, manager, mock_websocket):
        """测试订阅频道"""
        await manager.connect(
            websocket=mock_websocket,
            user_id="user-001",
            channels=[],
        )
        
        result = await manager.subscribe("user-001", WSChannel.RISK)
        
        assert result is True
        assert WSChannel.RISK in manager.get_user_channels("user-001")
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, manager, mock_websocket):
        """测试取消订阅"""
        await manager.connect(
            websocket=mock_websocket,
            user_id="user-001",
            channels=[WSChannel.TRADING, WSChannel.RISK],
        )
        
        result = await manager.unsubscribe("user-001", WSChannel.RISK)
        
        assert result is True
        assert WSChannel.RISK not in manager.get_user_channels("user-001")
        assert WSChannel.TRADING in manager.get_user_channels("user-001")

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager, mock_websocket):
        """测试发送消息给用户"""
        await manager.connect(
            websocket=mock_websocket,
            user_id="user-001",
            channels=[WSChannel.TRADING],
        )
        
        message = WSMessage(
            channel=WSChannel.TRADING,
            type="position",
            action=WSAction.UPDATE,
            data={"symbol": "BTCUSDT"},
        )
        
        result = await manager.send_to_user("user-001", message)
        
        assert result is True
        mock_websocket.send_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_to_nonexistent_user(self, manager):
        """测试发送消息给不存在的用户"""
        message = WSMessage(
            channel=WSChannel.TRADING,
            type="position",
            action=WSAction.UPDATE,
            data={},
        )
        
        result = await manager.send_to_user("nonexistent", message)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, manager):
        """测试广播消息到频道"""
        # 创建多个连接
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()
        
        await manager.connect(ws1, "user-001", [WSChannel.TRADING])
        await manager.connect(ws2, "user-002", [WSChannel.TRADING])
        
        message = WSMessage(
            channel=WSChannel.TRADING,
            type="order",
            action=WSAction.CREATE,
            data={"order_id": "123"},
        )
        
        count = await manager.broadcast_to_channel(WSChannel.TRADING, message)
        
        assert count == 2
        ws1.send_text.assert_called()
        ws2.send_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self, manager):
        """测试广播时排除用户"""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()
        
        await manager.connect(ws1, "user-001", [WSChannel.STATE])
        await manager.connect(ws2, "user-002", [WSChannel.STATE])
        
        # 重置 mock 计数（连接时会发送确认消息）
        ws1.send_text.reset_mock()
        ws2.send_text.reset_mock()
        
        message = WSMessage(
            channel=WSChannel.STATE,
            type="state_change",
            action=WSAction.UPDATE,
            data={},
        )
        
        count = await manager.broadcast_to_channel(
            WSChannel.STATE,
            message,
            exclude_users={"user-001"},
        )
        
        assert count == 1
        ws1.send_text.assert_not_called()
        ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats(self, manager, mock_websocket):
        """测试获取统计信息"""
        await manager.connect(
            websocket=mock_websocket,
            user_id="user-001",
            channels=[WSChannel.TRADING, WSChannel.RISK],
        )
        
        stats = manager.get_stats()
        
        assert stats["total_connections"] == 1
        assert stats["channels"]["trading"] == 1
        assert stats["channels"]["risk"] == 1
        assert stats["channels"]["state"] == 0
    
    @pytest.mark.asyncio
    async def test_reconnect_replaces_old_connection(self, manager):
        """测试重连时替换旧连接"""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.close = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        
        await manager.connect(ws1, "user-001", [WSChannel.TRADING])
        await manager.connect(ws2, "user-001", [WSChannel.RISK])
        
        assert manager.connection_count == 1
        ws1.close.assert_called_once()
        
        channels = manager.get_user_channels("user-001")
        assert WSChannel.RISK in channels
        assert WSChannel.TRADING not in channels


class TestWSPublisher:
    """WSPublisher 测试"""
    
    @pytest.mark.asyncio
    async def test_publish_position_update(self):
        """测试发布持仓更新"""
        with patch("src.api.websocket.publisher.ws_manager") as mock_manager:
            mock_manager.send_to_user = AsyncMock(return_value=True)
            
            result = await WSPublisher.publish_position_update(
                user_id="user-001",
                position_data={"symbol": "BTCUSDT", "quantity": 0.5},
            )
            
            assert result is True
            mock_manager.send_to_user.assert_called_once()
            
            call_args = mock_manager.send_to_user.call_args
            assert call_args[0][0] == "user-001"
            message = call_args[0][1]
            assert message.channel == WSChannel.TRADING
            assert message.type == "position"
    
    @pytest.mark.asyncio
    async def test_publish_order_update(self):
        """测试发布订单更新"""
        with patch("src.api.websocket.publisher.ws_manager") as mock_manager:
            mock_manager.send_to_user = AsyncMock(return_value=True)
            
            result = await WSPublisher.publish_order_update(
                user_id="user-001",
                order_data={"order_id": "123", "status": "FILLED"},
                action=WSAction.UPDATE,
            )
            
            assert result is True
            message = mock_manager.send_to_user.call_args[0][1]
            assert message.type == "order"
            assert message.action == WSAction.UPDATE

    @pytest.mark.asyncio
    async def test_publish_risk_update(self):
        """测试发布风控更新"""
        with patch("src.api.websocket.publisher.ws_manager") as mock_manager:
            mock_manager.send_to_user = AsyncMock(return_value=True)
            
            result = await WSPublisher.publish_risk_update(
                user_id="user-001",
                risk_data={"drawdown": 0.05, "daily_loss": 0.01},
            )
            
            assert result is True
            message = mock_manager.send_to_user.call_args[0][1]
            assert message.channel == WSChannel.RISK
            assert message.type == "metrics"
    
    @pytest.mark.asyncio
    async def test_publish_state_change(self):
        """测试发布状态变更"""
        with patch("src.api.websocket.publisher.ws_manager") as mock_manager:
            mock_manager.broadcast_to_channel = AsyncMock(return_value=5)
            
            count = await WSPublisher.publish_state_change(
                new_state="EXECUTING",
                old_state="READY",
                reason="信号触发",
            )
            
            assert count == 5
            mock_manager.broadcast_to_channel.assert_called_once()
            
            call_args = mock_manager.broadcast_to_channel.call_args
            assert call_args[0][0] == WSChannel.STATE
            message = call_args[0][1]
            assert message.type == "state_change"
            assert message.data["new_state"] == "EXECUTING"
    
    @pytest.mark.asyncio
    async def test_broadcast_system_message(self):
        """测试广播系统消息"""
        with patch("src.api.websocket.publisher.ws_manager") as mock_manager:
            mock_manager.broadcast_to_all = AsyncMock(return_value=10)
            
            count = await WSPublisher.broadcast_system_message(
                message_text="系统维护通知",
                level="warning",
            )
            
            assert count == 10
            message = mock_manager.broadcast_to_all.call_args[0][0]
            assert message.type == "system_message"
            assert message.data["message"] == "系统维护通知"
            assert message.data["level"] == "warning"
