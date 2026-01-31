"""
BTC 自动交易系统 — Binance 客户端

Binance Futures API 集成，包含 REST 和 WebSocket。
"""

import asyncio
import hashlib
import hmac
import inspect
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urlencode

from src.common.enums import OrderSide, OrderStatus, OrderType
from src.common.logging import get_logger
from src.common.models import MarketBar, Order
from src.common.retry import retry_with_backoff
from src.common.utils import utc_now

from .base import ExchangeClient, ExchangeOrderResult, Position

logger = get_logger(__name__)


@dataclass
class AccountInfo:
    """账户信息"""
    total_balance: float = 0.0
    available_balance: float = 0.0
    unrealized_pnl: float = 0.0
    margin_balance: float = 0.0
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class TickerPrice:
    """实时价格"""
    symbol: str
    price: float
    timestamp: datetime = field(default_factory=utc_now)


class BinanceClient(ExchangeClient):
    """
    Binance Futures 客户端
    
    支持：
    - REST API：下单、撤单、查询
    - WebSocket：实时 K 线、深度、成交
    """
    
    BASE_URL = "https://fapi.binance.com"
    WS_URL = "wss://fstream.binance.com/ws"
    
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self._client: Any = None
        self._connected = False
        
        # WebSocket
        self._ws: Any = None
        self._ws_connected = False
        self._ws_task: asyncio.Task | None = None
        self._ws_callbacks: dict[str, list[Callable]] = {}
        self._ws_reconnect_delay = 5
        
        # 缓存
        self._ticker_cache: dict[str, TickerPrice] = {}
        self._position_cache: dict[str, Position] = {}
        
        if testnet:
            self.BASE_URL = "https://testnet.binancefuture.com"
            self.WS_URL = "wss://stream.binancefuture.com/ws"
    
    @property
    def name(self) -> str:
        return "binance"
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def is_ws_connected(self) -> bool:
        return self._ws_connected
    
    # ========================================
    # 连接管理
    # ========================================
    
    async def connect(self) -> None:
        """建立 REST 连接"""
        import httpx
        self._client = httpx.AsyncClient(timeout=30.0)
        self._connected = True
        logger.info(f"Binance REST 客户端已连接 (testnet={self.testnet})")
    
    async def disconnect(self) -> None:
        """断开所有连接"""
        # 关闭 WebSocket
        await self.ws_disconnect()
        
        # 关闭 REST
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.info("Binance 客户端已断开")
    
    # ========================================
    # REST API - 签名和请求
    # ========================================
    
    def _sign(self, params: dict[str, Any]) -> str:
        """生成 HMAC SHA256 签名"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature
    
    def _get_headers(self) -> dict[str, str]:
        """获取请求头"""
        return {"X-MBX-APIKEY": self.api_key}
    
    @retry_with_backoff(max_retries=3, base_delay=0.5)
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> dict[str, Any] | list[Any]:
        """发送 REST 请求"""
        if not self._client:
            raise RuntimeError("客户端未连接")
        
        params = params or {}
        
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()
        
        if method == "GET":
            response = await self._client.get(url, params=params, headers=headers)
        elif method == "POST":
            response = await self._client.post(url, params=params, headers=headers)
        elif method == "DELETE":
            response = await self._client.delete(url, params=params, headers=headers)
        elif method == "PUT":
            response = await self._client.put(url, params=params, headers=headers)
        else:
            raise ValueError(f"不支持的方法: {method}")
        
        response.raise_for_status()
        return response.json()
    
    # ========================================
    # REST API - 订单操作
    # ========================================
    
    async def place_order(self, order: Order) -> ExchangeOrderResult:
        """下单"""
        params: dict[str, Any] = {
            "symbol": order.symbol,
            "side": order.side.value.upper(),
            "type": order.order_type.value.upper(),
            "quantity": str(order.quantity),
            "newClientOrderId": order.order_id,
        }
        
        # 限价单需要价格
        if order.order_type == OrderType.LIMIT and order.price:
            params["price"] = str(order.price)
            params["timeInForce"] = "GTC"
        
        # 止损/止盈单
        if order.stop_price:
            params["stopPrice"] = str(order.stop_price)
        
        try:
            result = await self._request("POST", "/fapi/v1/order", params, signed=True)
            
            status = self._parse_status(result.get("status", ""))
            
            return ExchangeOrderResult(
                order_id=order.order_id,
                exchange_order_id=str(result.get("orderId", "")),
                status=status,
                executed_quantity=float(result.get("executedQty", 0)),
                executed_price=float(result.get("avgPrice", 0) or 0),
                commission=0.0,
                raw_response=result,
            )
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return ExchangeOrderResult(
                order_id=order.order_id,
                exchange_order_id="",
                status=OrderStatus.REJECTED,
                executed_quantity=0,
                executed_price=0,
            )
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """撤单"""
        try:
            params = {
                "symbol": symbol,
                "origClientOrderId": order_id,
            }
            await self._request("DELETE", "/fapi/v1/order", params, signed=True)
            logger.info(f"撤单成功: {order_id}")
            return True
        except Exception as e:
            logger.error(f"撤单失败: {order_id}, {e}")
            return False
    
    async def cancel_all_orders(self, symbol: str) -> bool:
        """撤销所有订单"""
        try:
            params = {"symbol": symbol}
            await self._request("DELETE", "/fapi/v1/allOpenOrders", params, signed=True)
            logger.info(f"撤销所有订单: {symbol}")
            return True
        except Exception as e:
            logger.error(f"撤销所有订单失败: {symbol}, {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> OrderStatus:
        """获取订单状态"""
        try:
            params = {
                "symbol": symbol,
                "origClientOrderId": order_id,
            }
            result = await self._request("GET", "/fapi/v1/order", params, signed=True)
            return self._parse_status(result.get("status", ""))
        except Exception as e:
            logger.error(f"获取订单状态失败: {order_id}, {e}")
            return OrderStatus.PENDING
    
    async def get_open_orders(self, symbol: str | None = None) -> list[dict]:
        """获取未成交订单"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol
            result = await self._request("GET", "/fapi/v1/openOrders", params, signed=True)
            return result
        except Exception as e:
            logger.error(f"获取未成交订单失败: {e}")
            return []
    
    async def get_order_history(self, symbol: str, limit: int = 50) -> list[dict]:
        """获取订单历史"""
        try:
            params = {
                "symbol": symbol,
                "limit": limit,
            }
            result = await self._request("GET", "/fapi/v1/allOrders", params, signed=True)
            return result
        except Exception as e:
            logger.error(f"获取订单历史失败: {e}")
            return []
    
    async def get_trade_history(self, symbol: str, limit: int = 50) -> list[dict]:
        """获取成交历史"""
        try:
            params = {
                "symbol": symbol,
                "limit": limit,
            }
            result = await self._request("GET", "/fapi/v1/userTrades", params, signed=True)
            return result
        except Exception as e:
            logger.error(f"获取成交历史失败: {e}")
            return []
    
    # ========================================
    # REST API - 账户和仓位
    # ========================================
    
    async def get_position(self, symbol: str) -> Position:
        """获取仓位"""
        try:
            result = await self._request("GET", "/fapi/v2/positionRisk", signed=True)
            
            for pos in result:
                if pos.get("symbol") == symbol:
                    quantity = float(pos.get("positionAmt", 0))
                    side = "LONG" if quantity > 0 else "SHORT" if quantity < 0 else "NONE"
                    
                    position = Position(
                        symbol=symbol,
                        side=side,
                        quantity=abs(quantity),
                        entry_price=float(pos.get("entryPrice", 0)),
                        unrealized_pnl=float(pos.get("unRealizedProfit", 0)),
                        leverage=int(pos.get("leverage", 1)),
                        margin=float(pos.get("isolatedMargin", 0) or pos.get("positionInitialMargin", 0)),
                    )
                    self._position_cache[symbol] = position
                    return position
            
            return Position(symbol=symbol, side="NONE", quantity=0, entry_price=0)
        except Exception as e:
            logger.error(f"获取仓位失败: {symbol}, {e}")
            # 返回缓存
            return self._position_cache.get(
                symbol, 
                Position(symbol=symbol, side="NONE", quantity=0, entry_price=0)
            )
    
    async def get_all_positions(self) -> list[Position]:
        """获取所有仓位"""
        try:
            result = await self._request("GET", "/fapi/v2/positionRisk", signed=True)
            positions = []
            
            for pos in result:
                quantity = float(pos.get("positionAmt", 0))
                if quantity == 0:
                    continue
                
                side = "LONG" if quantity > 0 else "SHORT"
                symbol = pos.get("symbol", "")
                
                position = Position(
                    symbol=symbol,
                    side=side,
                    quantity=abs(quantity),
                    entry_price=float(pos.get("entryPrice", 0)),
                    unrealized_pnl=float(pos.get("unRealizedProfit", 0)),
                    leverage=int(pos.get("leverage", 1)),
                    margin=float(pos.get("isolatedMargin", 0) or pos.get("positionInitialMargin", 0)),
                )
                positions.append(position)
                self._position_cache[symbol] = position
            
            return positions
        except Exception as e:
            logger.error(f"获取所有仓位失败: {e}")
            return list(self._position_cache.values())
    
    async def get_balance(self) -> float:
        """获取可用余额（USDT）"""
        try:
            result = await self._request("GET", "/fapi/v2/balance", signed=True)
            
            for asset in result:
                if asset.get("asset") == "USDT":
                    return float(asset.get("availableBalance", 0))
            
            return 0.0
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0
    
    async def get_account_info(self) -> AccountInfo:
        """获取账户详细信息"""
        try:
            result = await self._request("GET", "/fapi/v2/account", signed=True)
            
            return AccountInfo(
                total_balance=float(result.get("totalWalletBalance", 0)),
                available_balance=float(result.get("availableBalance", 0)),
                unrealized_pnl=float(result.get("totalUnrealizedProfit", 0)),
                margin_balance=float(result.get("totalMarginBalance", 0)),
            )
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return AccountInfo()
    
    # ========================================
    # REST API - 杠杆和保证金
    # ========================================
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """设置杠杆"""
        try:
            params = {
                "symbol": symbol,
                "leverage": leverage,
            }
            await self._request("POST", "/fapi/v1/leverage", params, signed=True)
            logger.info(f"设置杠杆: {symbol} = {leverage}x")
            return True
        except Exception as e:
            logger.error(f"设置杠杆失败: {symbol}, {e}")
            return False
    
    async def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> bool:
        """设置保证金模式（ISOLATED/CROSSED）"""
        try:
            params = {
                "symbol": symbol,
                "marginType": margin_type,
            }
            await self._request("POST", "/fapi/v1/marginType", params, signed=True)
            logger.info(f"设置保证金模式: {symbol} = {margin_type}")
            return True
        except Exception as e:
            # 如果已经是该模式，会报错，忽略
            if "No need to change margin type" in str(e):
                return True
            logger.error(f"设置保证金模式失败: {symbol}, {e}")
            return False
    
    # ========================================
    # REST API - 市场数据
    # ========================================
    
    async def get_ticker_price(self, symbol: str) -> float:
        """获取最新价格"""
        try:
            params = {"symbol": symbol}
            result = await self._request("GET", "/fapi/v1/ticker/price", params)
            price = float(result.get("price", 0))
            self._ticker_cache[symbol] = TickerPrice(symbol=symbol, price=price)
            return price
        except Exception as e:
            logger.error(f"获取价格失败: {symbol}, {e}")
            cached = self._ticker_cache.get(symbol)
            return cached.price if cached else 0.0
    
    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[MarketBar]:
        """获取 K 线数据"""
        try:
            params: dict[str, Any] = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            }
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            
            result = await self._request("GET", "/fapi/v1/klines", params)
            
            bars = []
            for row in result:
                bars.append(MarketBar(
                    ts=int(row[0]),
                    symbol=symbol,
                    interval=interval,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    quote_volume=float(row[7]),
                    trades=int(row[8]),
                ))
            return bars
        except Exception as e:
            logger.error(f"获取 K 线失败: {symbol}, {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> float:
        """获取当前资金费率"""
        try:
            params = {"symbol": symbol}
            result = await self._request("GET", "/fapi/v1/premiumIndex", params)
            return float(result.get("lastFundingRate", 0))
        except Exception as e:
            logger.error(f"获取资金费率失败: {symbol}, {e}")
            return 0.0
    
    async def get_exchange_info(self, symbol: str | None = None) -> dict:
        """获取交易规则"""
        try:
            result = await self._request("GET", "/fapi/v1/exchangeInfo")
            if symbol:
                for s in result.get("symbols", []):
                    if s.get("symbol") == symbol:
                        return s
                return {}
            return result
        except Exception as e:
            logger.error(f"获取交易规则失败: {e}")
            return {}
    
    # ========================================
    # WebSocket - 连接管理
    # ========================================
    
    async def ws_connect(self, streams: list[str]) -> None:
        """
        连接 WebSocket
        
        Args:
            streams: 订阅的流，如 ["btcusdt@kline_1m", "btcusdt@depth"]
        """
        import websockets
        
        stream_path = "/".join(streams)
        url = f"{self.WS_URL}/{stream_path}"
        
        try:
            self._ws = await websockets.connect(url)
            self._ws_connected = True
            logger.info(f"WebSocket 已连接: {streams}")
            
            # 启动消息处理任务
            self._ws_task = asyncio.create_task(self._ws_message_loop())
        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e}")
            self._ws_connected = False
    
    async def ws_disconnect(self) -> None:
        """断开 WebSocket"""
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        self._ws_connected = False
        logger.info("WebSocket 已断开")
    
    async def _ws_message_loop(self) -> None:
        """WebSocket 消息处理循环"""
        while self._ws_connected and self._ws:
            try:
                message = await self._ws.recv()
                data = json.loads(message)
                await self._handle_ws_message(data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket 消息处理错误: {e}")
                if not self._ws_connected:
                    break
                # 尝试重连
                await asyncio.sleep(self._ws_reconnect_delay)
    
    async def _handle_ws_message(self, data: dict) -> None:
        """处理 WebSocket 消息"""
        event_type = data.get("e", "")
        
        # K 线数据
        if event_type == "kline":
            await self._handle_kline(data)
        # 深度数据
        elif event_type == "depthUpdate":
            await self._handle_depth(data)
        # 成交数据
        elif event_type == "trade" or event_type == "aggTrade":
            await self._handle_trade(data)
        # 标记价格
        elif event_type == "markPriceUpdate":
            await self._handle_mark_price(data)
        # 账户更新
        elif event_type == "ACCOUNT_UPDATE":
            await self._handle_account_update(data)
        # 订单更新
        elif event_type == "ORDER_TRADE_UPDATE":
            await self._handle_order_update(data)
        
        # 触发回调
        callbacks = self._ws_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"回调执行错误: {e}")
    
    def on_ws_event(self, event_type: str, callback: Callable) -> None:
        """注册 WebSocket 事件回调"""
        if event_type not in self._ws_callbacks:
            self._ws_callbacks[event_type] = []
        self._ws_callbacks[event_type].append(callback)
    
    async def _handle_kline(self, data: dict) -> None:
        """处理 K 线数据"""
        k = data.get("k", {})
        symbol = k.get("s", "")
        
        bar = MarketBar(
            ts=k.get("t", 0),
            symbol=symbol,
            interval=k.get("i", ""),
            open=float(k.get("o", 0)),
            high=float(k.get("h", 0)),
            low=float(k.get("l", 0)),
            close=float(k.get("c", 0)),
            volume=float(k.get("v", 0)),
            quote_volume=float(k.get("q", 0)),
            trades=int(k.get("n", 0)),
        )
        
        # 更新价格缓存
        self._ticker_cache[symbol] = TickerPrice(symbol=symbol, price=bar.close)
        
        logger.debug(f"K线: {symbol} {bar.interval} close={bar.close}")
    
    async def _handle_depth(self, data: dict) -> None:
        """处理深度数据"""
        # 可扩展：更新订单簿
        pass
    
    async def _handle_trade(self, data: dict) -> None:
        """处理成交数据"""
        symbol = data.get("s", "")
        price = float(data.get("p", 0))
        self._ticker_cache[symbol] = TickerPrice(symbol=symbol, price=price)
    
    async def _handle_mark_price(self, data: dict) -> None:
        """处理标记价格"""
        symbol = data.get("s", "")
        price = float(data.get("p", 0))
        self._ticker_cache[symbol] = TickerPrice(symbol=symbol, price=price)
    
    async def _handle_account_update(self, data: dict) -> None:
        """处理账户更新"""
        logger.info(f"账户更新: {data}")
    
    async def _handle_order_update(self, data: dict) -> None:
        """处理订单更新"""
        o = data.get("o", {})
        order_id = o.get("c", "")
        status = o.get("X", "")
        logger.info(f"订单更新: {order_id} -> {status}")
    
    # ========================================
    # WebSocket - 用户数据流
    # ========================================
    
    async def start_user_data_stream(self) -> str | None:
        """启动用户数据流，返回 listenKey"""
        try:
            result = await self._request("POST", "/fapi/v1/listenKey", signed=False)
            listen_key = result.get("listenKey", "")
            logger.info(f"用户数据流已启动: {listen_key[:20]}...")
            return listen_key
        except Exception as e:
            logger.error(f"启动用户数据流失败: {e}")
            return None
    
    async def keepalive_user_data_stream(self) -> bool:
        """保持用户数据流"""
        try:
            await self._request("PUT", "/fapi/v1/listenKey", signed=False)
            return True
        except Exception as e:
            logger.error(f"保持用户数据流失败: {e}")
            return False
    
    async def close_user_data_stream(self) -> bool:
        """关闭用户数据流"""
        try:
            await self._request("DELETE", "/fapi/v1/listenKey", signed=False)
            return True
        except Exception as e:
            logger.error(f"关闭用户数据流失败: {e}")
            return False
    
    # ========================================
    # 辅助方法
    # ========================================
    
    def _parse_status(self, status: str) -> OrderStatus:
        """解析订单状态"""
        status_map = {
            "NEW": OrderStatus.SUBMITTED,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.CANCELLED,
        }
        return status_map.get(status, OrderStatus.PENDING)
    
    def get_cached_price(self, symbol: str) -> float:
        """获取缓存的价格"""
        cached = self._ticker_cache.get(symbol)
        return cached.price if cached else 0.0
    
    def get_cached_position(self, symbol: str) -> Position | None:
        """获取缓存的仓位"""
        return self._position_cache.get(symbol)
