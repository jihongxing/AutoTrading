"""
BTC 自动交易系统 — WebSocket 连接管理器

管理 WebSocket 连接、消息广播和订阅。
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from src.common.logging import get_logger
from src.common.utils import utc_now

logger = get_logger(__name__)


class WSChannel(str, Enum):
    """WebSocket 频道"""
    TRADING = "trading"      # 订单、持仓
    RISK = "risk"            # 风控指标
    STATE = "state"          # 状态机
    MARKET = "market"        # 行情数据


class WSAction(str, Enum):
    """消息动作类型"""
    UPDATE = "update"
    CREATE = "create"
    DELETE = "delete"
    SNAPSHOT = "snapshot"    # 全量快照


@dataclass
class WSMessage:
    """WebSocket 消息"""
    channel: WSChannel
    type: str                # position, order, risk, state, kline 等
    action: WSAction
    data: Any
    timestamp: datetime = field(default_factory=utc_now)
    
    def to_json(self) -> str:
        return json.dumps({
            "channel": self.channel.value,
            "type": self.type,
            "action": self.action.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }, ensure_ascii=False)


@dataclass
class Connection:
    """WebSocket 连接"""
    websocket: WebSocket
    user_id: str
    channels: set[WSChannel] = field(default_factory=set)
    subscriptions: dict[str, Any] = field(default_factory=dict)  # 额外订阅参数
    connected_at: datetime = field(default_factory=utc_now)
    last_ping: datetime = field(default_factory=utc_now)


class ConnectionManager:
    """
    WebSocket 连接管理器
    
    功能：
    - 管理用户连接
    - 频道订阅
    - 消息广播
    - 心跳检测
    """
    
    def __init__(self):
        # user_id -> Connection
        self._connections: dict[str, Connection] = {}
        # channel -> set[user_id]
        self._channel_subscribers: dict[WSChannel, set[str]] = {
            channel: set() for channel in WSChannel
        }
        # 心跳任务
        self._heartbeat_task: asyncio.Task | None = None
        self._running = False
    
    @property
    def connection_count(self) -> int:
        return len(self._connections)
    
    def get_channel_count(self, channel: WSChannel) -> int:
        return len(self._channel_subscribers.get(channel, set()))
    
    # ========================================
    # 连接管理
    # ========================================
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        channels: list[WSChannel] | None = None,
    ) -> Connection:
        """
        建立连接
        
        Args:
            websocket: WebSocket 实例
            user_id: 用户 ID
            channels: 初始订阅频道
        
        Returns:
            Connection 实例
        """
        await websocket.accept()
        
        # 如果已有连接，先断开
        if user_id in self._connections:
            await self.disconnect(user_id)
        
        # 创建连接
        connection = Connection(
            websocket=websocket,
            user_id=user_id,
            channels=set(channels) if channels else set(),
        )
        self._connections[user_id] = connection
        
        # 订阅频道
        for channel in connection.channels:
            self._channel_subscribers[channel].add(user_id)
        
        logger.info(f"WebSocket 连接: user={user_id}, channels={[c.value for c in connection.channels]}")
        
        # 发送连接确认
        await self.send_to_user(user_id, WSMessage(
            channel=WSChannel.STATE,
            type="connection",
            action=WSAction.CREATE,
            data={"status": "connected", "user_id": user_id},
        ))
        
        return connection
    
    async def disconnect(self, user_id: str) -> None:
        """断开连接"""
        connection = self._connections.pop(user_id, None)
        if connection:
            # 取消订阅
            for channel in connection.channels:
                self._channel_subscribers[channel].discard(user_id)
            
            try:
                await connection.websocket.close()
            except Exception:
                pass
            
            logger.info(f"WebSocket 断开: user={user_id}")
    
    async def disconnect_all(self) -> None:
        """断开所有连接"""
        for user_id in list(self._connections.keys()):
            await self.disconnect(user_id)

    # ========================================
    # 订阅管理
    # ========================================
    
    async def subscribe(
        self,
        user_id: str,
        channel: WSChannel,
        params: dict | None = None,
    ) -> bool:
        """
        订阅频道
        
        Args:
            user_id: 用户 ID
            channel: 频道
            params: 订阅参数（如 symbol）
        
        Returns:
            是否成功
        """
        connection = self._connections.get(user_id)
        if not connection:
            return False
        
        connection.channels.add(channel)
        self._channel_subscribers[channel].add(user_id)
        
        if params:
            connection.subscriptions[channel.value] = params
        
        logger.debug(f"订阅频道: user={user_id}, channel={channel.value}")
        return True
    
    async def unsubscribe(self, user_id: str, channel: WSChannel) -> bool:
        """取消订阅"""
        connection = self._connections.get(user_id)
        if not connection:
            return False
        
        connection.channels.discard(channel)
        self._channel_subscribers[channel].discard(user_id)
        connection.subscriptions.pop(channel.value, None)
        
        logger.debug(f"取消订阅: user={user_id}, channel={channel.value}")
        return True
    
    # ========================================
    # 消息发送
    # ========================================
    
    async def send_to_user(self, user_id: str, message: WSMessage) -> bool:
        """
        发送消息给指定用户
        
        Args:
            user_id: 用户 ID
            message: 消息
        
        Returns:
            是否成功
        """
        connection = self._connections.get(user_id)
        if not connection:
            return False
        
        try:
            await connection.websocket.send_text(message.to_json())
            return True
        except Exception as e:
            logger.error(f"发送消息失败: user={user_id}, error={e}")
            await self.disconnect(user_id)
            return False
    
    async def broadcast_to_channel(
        self,
        channel: WSChannel,
        message: WSMessage,
        exclude_users: set[str] | None = None,
    ) -> int:
        """
        广播消息到频道
        
        Args:
            channel: 频道
            message: 消息
            exclude_users: 排除的用户
        
        Returns:
            成功发送数量
        """
        subscribers = self._channel_subscribers.get(channel, set())
        if exclude_users:
            subscribers = subscribers - exclude_users
        
        success_count = 0
        failed_users = []
        
        for user_id in subscribers:
            try:
                connection = self._connections.get(user_id)
                if connection:
                    await connection.websocket.send_text(message.to_json())
                    success_count += 1
            except Exception as e:
                logger.error(f"广播失败: user={user_id}, error={e}")
                failed_users.append(user_id)
        
        # 清理失败连接
        for user_id in failed_users:
            await self.disconnect(user_id)
        
        return success_count
    
    async def broadcast_to_all(
        self,
        message: WSMessage,
        exclude_users: set[str] | None = None,
    ) -> int:
        """广播消息给所有用户"""
        users = set(self._connections.keys())
        if exclude_users:
            users = users - exclude_users
        
        success_count = 0
        for user_id in users:
            if await self.send_to_user(user_id, message):
                success_count += 1
        
        return success_count

    # ========================================
    # 心跳检测
    # ========================================
    
    async def start_heartbeat(self, interval: int = 30) -> None:
        """启动心跳检测"""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))
        logger.info(f"WebSocket 心跳检测已启动, interval={interval}s")
    
    async def stop_heartbeat(self) -> None:
        """停止心跳检测"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        logger.info("WebSocket 心跳检测已停止")
    
    async def _heartbeat_loop(self, interval: int) -> None:
        """心跳循环"""
        while self._running:
            try:
                await asyncio.sleep(interval)
                await self._send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳错误: {e}")
    
    async def _send_heartbeat(self) -> None:
        """发送心跳"""
        message = WSMessage(
            channel=WSChannel.STATE,
            type="heartbeat",
            action=WSAction.UPDATE,
            data={"timestamp": utc_now().isoformat()},
        )
        
        failed_users = []
        for user_id, connection in list(self._connections.items()):
            try:
                await connection.websocket.send_text(message.to_json())
                connection.last_ping = utc_now()
            except Exception:
                failed_users.append(user_id)
        
        # 清理失败连接
        for user_id in failed_users:
            await self.disconnect(user_id)
    
    async def handle_pong(self, user_id: str) -> None:
        """处理 pong 响应"""
        connection = self._connections.get(user_id)
        if connection:
            connection.last_ping = utc_now()
    
    # ========================================
    # 工具方法
    # ========================================
    
    def get_connection(self, user_id: str) -> Connection | None:
        """获取连接"""
        return self._connections.get(user_id)
    
    def is_connected(self, user_id: str) -> bool:
        """检查用户是否连接"""
        return user_id in self._connections
    
    def get_user_channels(self, user_id: str) -> list[WSChannel]:
        """获取用户订阅的频道"""
        connection = self._connections.get(user_id)
        if connection:
            return list(connection.channels)
        return []
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_connections": self.connection_count,
            "channels": {
                channel.value: self.get_channel_count(channel)
                for channel in WSChannel
            },
        }


# 全局连接管理器实例
ws_manager = ConnectionManager()
