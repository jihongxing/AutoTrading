"""
BTC 自动交易系统 — 数据路由

提供市场数据查询接口。
"""

from datetime import datetime

from fastapi import APIRouter, Query

from src.api.auth import CurrentUser
from src.api.schemas import (
    ApiResponse,
    FundingRateResponse,
    LiquidationResponse,
    MarketBarsResponse,
)

router = APIRouter(prefix="/market", tags=["数据"])


@router.get("/bars", response_model=ApiResponse[MarketBarsResponse])
async def get_market_bars(
    user: CurrentUser,
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = Query(100, le=1000),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> ApiResponse[MarketBarsResponse]:
    """
    获取 K 线数据
    
    返回指定交易对的 K 线数据。
    注：当前返回空数据，需要配置 QuestDB 后才能获取真实数据。
    """
    # 暂时返回空数据
    return ApiResponse(data=MarketBarsResponse(symbol=symbol, interval=interval, bars=[]))


@router.get("/funding-rates", response_model=ApiResponse[list[FundingRateResponse]])
async def get_funding_rates(
    user: CurrentUser,
    symbol: str = "BTCUSDT",
    limit: int = Query(24, le=100),
) -> ApiResponse[list[FundingRateResponse]]:
    """
    获取资金费率
    
    返回最近的资金费率数据。
    """
    # 暂时返回空数据
    return ApiResponse(data=[])


@router.get("/liquidations", response_model=ApiResponse[list[LiquidationResponse]])
async def get_liquidations(
    user: CurrentUser,
    symbol: str = "BTCUSDT",
    limit: int = Query(50, le=200),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> ApiResponse[list[LiquidationResponse]]:
    """
    获取清算数据
    
    返回最近的清算事件。
    """
    # 暂时返回空数据
    return ApiResponse(data=[])
