"""
BTC 自动交易系统 — WebSocket 路由

提供 WebSocket 端点。
"""

import json
from typing import Any

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from src.api.auth import JWT_ALGORITHM, JWT_SECRET, TokenType
from src.common.logging import get_logger
from src.common.utils import utc_now

from .manager import WSAction, WSChannel, WSMessage, ws_manager

logger = get_logger(__name__)

ws_router = APIRouter(tags=["WebSocket"])


async def authenticate_websocket(websocket: WebSocket, token: str | None) -> str | None:
    """
    WebSocket 认证
    
    Args:
        websocket: WebSocket 实例
        token: JWT Token
    
    Returns:
        user_id 或 None
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        if payload.get("type") != TokenType.ACCESS.value:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        
        return payload.get("sub")
        
    except jwt.ExpiredSignatureError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None


@ws_router.websocket("/ws/trading")
async def ws_trading(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """
    交易数据 WebSocket
    
    推送：订单、持仓更新
    """
    user_id = await authenticate_websocket(websocket, token)
    if not user_id:
        return
    
    connection = await ws_manager.connect(
        websocket=websocket,
        user_id=user_id,
        channels=[WSChannel.TRADING],
    )
    
    try:
        while True:
            data = await websocket.receive_text()
            await handle_client_message(user_id, data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: user={user_id}, error={e}")
        await ws_manager.disconnect(user_id)


@ws_router.websocket("/ws/risk")
async def ws_risk(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """
    风控数据 WebSocket
    
    推送：风控指标、风控事件
    """
    user_id = await authenticate_websocket(websocket, token)
    if not user_id:
        return
    
    connection = await ws_manager.connect(
        websocket=websocket,
        user_id=user_id,
        channels=[WSChannel.RISK],
    )
    
    try:
        while True:
            data = await websocket.receive_text()
            await handle_client_message(user_id, data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: user={user_id}, error={e}")
        await ws_manager.disconnect(user_id)


@ws_router.websocket("/ws/state")
async def ws_state(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """
    状态机 WebSocket
    
    推送：状态机变更
    """
    user_id = await authenticate_websocket(websocket, token)
    if not user_id:
        return
    
    connection = await ws_manager.connect(
        websocket=websocket,
        user_id=user_id,
        channels=[WSChannel.STATE],
    )
    
    try:
        while True:
            data = await websocket.receive_text()
            await handle_client_message(user_id, data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: user={user_id}, error={e}")
        await ws_manager.disconnect(user_id)


@ws_router.websocket("/ws/market")
async def ws_market(
    websocket: WebSocket,
    token: str | None = Query(None),
    symbol: str = Query("BTCUSDT"),
):
    """
    行情数据 WebSocket
    
    推送：K线、价格更新
    """
    user_id = await authenticate_websocket(websocket, token)
    if not user_id:
        return
    
    connection = await ws_manager.connect(
        websocket=websocket,
        user_id=user_id,
        channels=[WSChannel.MARKET],
    )
    
    # 保存订阅参数
    connection.subscriptions["market"] = {"symbol": symbol}
    
    try:
        while True:
            data = await websocket.receive_text()
            await handle_client_message(user_id, data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: user={user_id}, error={e}")
        await ws_manager.disconnect(user_id)


@ws_router.websocket("/ws/all")
async def ws_all(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """
    全频道 WebSocket
    
    订阅所有频道，适合 Dashboard 页面
    """
    user_id = await authenticate_websocket(websocket, token)
    if not user_id:
        return
    
    connection = await ws_manager.connect(
        websocket=websocket,
        user_id=user_id,
        channels=[WSChannel.TRADING, WSChannel.RISK, WSChannel.STATE],
    )
    
    try:
        while True:
            data = await websocket.receive_text()
            await handle_client_message(user_id, data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: user={user_id}, error={e}")
        await ws_manager.disconnect(user_id)


async def handle_client_message(user_id: str, data: str) -> None:
    """
    处理客户端消息
    
    支持的消息类型：
    - subscribe: 订阅频道
    - unsubscribe: 取消订阅
    - ping: 心跳
    """
    try:
        message = json.loads(data)
        msg_type = message.get("type", "")
        
        if msg_type == "ping":
            # 心跳响应
            await ws_manager.handle_pong(user_id)
            await ws_manager.send_to_user(user_id, WSMessage(
                channel=WSChannel.STATE,
                type="pong",
                action=WSAction.UPDATE,
                data={"timestamp": utc_now().isoformat()},
            ))
        
        elif msg_type == "subscribe":
            channel_name = message.get("channel", "")
            try:
                channel = WSChannel(channel_name)
                params = message.get("params", {})
                await ws_manager.subscribe(user_id, channel, params)
                await ws_manager.send_to_user(user_id, WSMessage(
                    channel=channel,
                    type="subscribed",
                    action=WSAction.UPDATE,
                    data={"channel": channel_name},
                ))
            except ValueError:
                logger.warning(f"无效频道: {channel_name}")
        
        elif msg_type == "unsubscribe":
            channel_name = message.get("channel", "")
            try:
                channel = WSChannel(channel_name)
                await ws_manager.unsubscribe(user_id, channel)
                await ws_manager.send_to_user(user_id, WSMessage(
                    channel=channel,
                    type="unsubscribed",
                    action=WSAction.UPDATE,
                    data={"channel": channel_name},
                ))
            except ValueError:
                pass
        
        else:
            logger.debug(f"未知消息类型: {msg_type}")
            
    except json.JSONDecodeError:
        logger.warning(f"无效 JSON: {data[:100]}")
    except Exception as e:
        logger.error(f"处理消息错误: {e}")
