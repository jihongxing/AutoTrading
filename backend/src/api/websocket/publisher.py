"""
BTC 自动交易系统 — WebSocket 事件发布器

提供业务层调用的事件发布接口。
"""

from typing import Any

from src.common.logging import get_logger
from src.common.utils import utc_now

from .manager import WSAction, WSChannel, WSMessage, ws_manager

logger = get_logger(__name__)


class WSPublisher:
    """
    WebSocket 事件发布器
    
    业务层通过此类发布事件到 WebSocket。
    """
    
    # ========================================
    # Trading 频道
    # ========================================
    
    @staticmethod
    async def publish_position_update(
        user_id: str,
        position_data: dict[str, Any],
    ) -> bool:
        """
        发布持仓更新
        
        Args:
            user_id: 用户 ID
            position_data: 持仓数据
        """
        message = WSMessage(
            channel=WSChannel.TRADING,
            type="position",
            action=WSAction.UPDATE,
            data=position_data,
        )
        return await ws_manager.send_to_user(user_id, message)
    
    @staticmethod
    async def publish_order_update(
        user_id: str,
        order_data: dict[str, Any],
        action: WSAction = WSAction.UPDATE,
    ) -> bool:
        """
        发布订单更新
        
        Args:
            user_id: 用户 ID
            order_data: 订单数据
            action: 动作类型（create/update/delete）
        """
        message = WSMessage(
            channel=WSChannel.TRADING,
            type="order",
            action=action,
            data=order_data,
        )
        return await ws_manager.send_to_user(user_id, message)
    
    @staticmethod
    async def publish_trade(
        user_id: str,
        trade_data: dict[str, Any],
    ) -> bool:
        """发布成交记录"""
        message = WSMessage(
            channel=WSChannel.TRADING,
            type="trade",
            action=WSAction.CREATE,
            data=trade_data,
        )
        return await ws_manager.send_to_user(user_id, message)

    # ========================================
    # Risk 频道
    # ========================================
    
    @staticmethod
    async def publish_risk_update(
        user_id: str,
        risk_data: dict[str, Any],
    ) -> bool:
        """
        发布风控指标更新
        
        Args:
            user_id: 用户 ID
            risk_data: 风控数据（drawdown, daily_loss 等）
        """
        message = WSMessage(
            channel=WSChannel.RISK,
            type="metrics",
            action=WSAction.UPDATE,
            data=risk_data,
        )
        return await ws_manager.send_to_user(user_id, message)
    
    @staticmethod
    async def publish_risk_event(
        user_id: str,
        event_data: dict[str, Any],
    ) -> bool:
        """
        发布风控事件
        
        Args:
            user_id: 用户 ID
            event_data: 事件数据
        """
        message = WSMessage(
            channel=WSChannel.RISK,
            type="event",
            action=WSAction.CREATE,
            data=event_data,
        )
        return await ws_manager.send_to_user(user_id, message)
    
    @staticmethod
    async def publish_risk_lock(
        user_id: str,
        lock_data: dict[str, Any],
    ) -> bool:
        """发布风控锁定事件"""
        message = WSMessage(
            channel=WSChannel.RISK,
            type="lock",
            action=WSAction.UPDATE,
            data=lock_data,
        )
        return await ws_manager.send_to_user(user_id, message)
    
    # ========================================
    # State 频道
    # ========================================
    
    @staticmethod
    async def publish_state_change(
        new_state: str,
        old_state: str | None = None,
        reason: str | None = None,
    ) -> int:
        """
        发布状态机变更（广播给所有用户）
        
        Args:
            new_state: 新状态
            old_state: 旧状态
            reason: 变更原因
        
        Returns:
            成功发送数量
        """
        message = WSMessage(
            channel=WSChannel.STATE,
            type="state_change",
            action=WSAction.UPDATE,
            data={
                "new_state": new_state,
                "old_state": old_state,
                "reason": reason,
                "timestamp": utc_now().isoformat(),
            },
        )
        return await ws_manager.broadcast_to_channel(WSChannel.STATE, message)
    
    @staticmethod
    async def publish_regime_change(
        new_regime: str,
        old_regime: str | None = None,
    ) -> int:
        """发布交易模式变更"""
        message = WSMessage(
            channel=WSChannel.STATE,
            type="regime_change",
            action=WSAction.UPDATE,
            data={
                "new_regime": new_regime,
                "old_regime": old_regime,
                "timestamp": utc_now().isoformat(),
            },
        )
        return await ws_manager.broadcast_to_channel(WSChannel.STATE, message)

    # ========================================
    # Market 频道
    # ========================================
    
    @staticmethod
    async def publish_kline(
        symbol: str,
        interval: str,
        kline_data: dict[str, Any],
    ) -> int:
        """
        发布 K 线数据
        
        Args:
            symbol: 交易对
            interval: 周期
            kline_data: K 线数据
        
        Returns:
            成功发送数量
        """
        message = WSMessage(
            channel=WSChannel.MARKET,
            type="kline",
            action=WSAction.UPDATE,
            data={
                "symbol": symbol,
                "interval": interval,
                **kline_data,
            },
        )
        
        # 只发送给订阅了该 symbol 的用户
        count = 0
        for user_id in ws_manager._channel_subscribers.get(WSChannel.MARKET, set()):
            connection = ws_manager.get_connection(user_id)
            if connection:
                sub_params = connection.subscriptions.get("market", {})
                if sub_params.get("symbol", "BTCUSDT") == symbol:
                    if await ws_manager.send_to_user(user_id, message):
                        count += 1
        return count
    
    @staticmethod
    async def publish_price(
        symbol: str,
        price: float,
    ) -> int:
        """
        发布价格更新
        
        Args:
            symbol: 交易对
            price: 最新价格
        
        Returns:
            成功发送数量
        """
        message = WSMessage(
            channel=WSChannel.MARKET,
            type="price",
            action=WSAction.UPDATE,
            data={
                "symbol": symbol,
                "price": price,
                "timestamp": utc_now().isoformat(),
            },
        )
        return await ws_manager.broadcast_to_channel(WSChannel.MARKET, message)
    
    # ========================================
    # 批量发布
    # ========================================
    
    @staticmethod
    async def publish_snapshot(
        user_id: str,
        channel: WSChannel,
        data_type: str,
        data: Any,
    ) -> bool:
        """
        发布全量快照
        
        用于连接建立后发送初始数据。
        """
        message = WSMessage(
            channel=channel,
            type=data_type,
            action=WSAction.SNAPSHOT,
            data=data,
        )
        return await ws_manager.send_to_user(user_id, message)
    
    @staticmethod
    async def broadcast_system_message(
        message_text: str,
        level: str = "info",
    ) -> int:
        """
        广播系统消息
        
        Args:
            message_text: 消息内容
            level: 级别（info/warning/error）
        
        Returns:
            成功发送数量
        """
        message = WSMessage(
            channel=WSChannel.STATE,
            type="system_message",
            action=WSAction.CREATE,
            data={
                "message": message_text,
                "level": level,
                "timestamp": utc_now().isoformat(),
            },
        )
        return await ws_manager.broadcast_to_all(message)


# 全局发布器实例
ws_publisher = WSPublisher()
