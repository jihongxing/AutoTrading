"""
BTC 自动交易系统 — 用户 API

用户信息、交易所配置、交易数据接口。
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...common.logging import get_logger
from ...common.utils import utc_now
from ...user.manager import UserManager
from ...user.models import SubscriptionPlan
from ..auth import CurrentActiveUser, CurrentUser, get_user_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["用户"])


# ========================================
# 请求/响应模型
# ========================================

class UpdateUserRequest(BaseModel):
    """更新用户请求"""
    email: str | None = Field(default=None, description="邮箱")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(description="原密码")
    new_password: str = Field(min_length=8, max_length=128, description="新密码")


class ExchangeConfigRequest(BaseModel):
    """交易所配置请求"""
    api_key: str = Field(description="API Key")
    api_secret: str = Field(description="API Secret")
    testnet: bool = Field(default=False, description="是否测试网")
    leverage: int = Field(default=10, ge=1, le=125, description="杠杆倍数")
    max_position_pct: float | None = Field(default=None, ge=0.01, le=1.0, description="最大仓位比例")


# ========================================
# 用户信息接口
# ========================================

@router.get("/me", response_model=dict[str, Any])
async def get_current_user_info(user: CurrentActiveUser) -> dict[str, Any]:
    """获取当前用户信息"""
    manager = get_user_manager()
    
    # 获取交易所配置状态
    exchange_config = await manager.get_exchange_config(user.user_id)
    has_exchange = exchange_config is not None and exchange_config.is_valid
    
    # 获取风控状态
    risk_state = await manager.get_risk_state(user.user_id)
    
    return {
        "success": True,
        "data": {
            "user": user.to_dict(),
            "has_exchange_config": has_exchange,
            "risk_state": risk_state.to_dict() if risk_state else None,
        },
        "timestamp": utc_now().isoformat(),
    }


@router.put("/me", response_model=dict[str, Any])
async def update_current_user(
    request: UpdateUserRequest,
    user: CurrentActiveUser,
) -> dict[str, Any]:
    """更新当前用户信息"""
    manager = get_user_manager()
    
    update_data = {}
    if request.email:
        # 检查邮箱唯一性
        existing = await manager.get_user_by_email(request.email)
        if existing and existing.user_id != user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "EMAIL_EXISTS", "message": "邮箱已被使用"},
            )
        update_data["email"] = request.email
    
    if update_data:
        await manager.update_user(user.user_id, **update_data)
    
    # 获取更新后的用户
    updated_user = await manager.get_user(user.user_id)
    
    return {
        "success": True,
        "data": {"user": updated_user.to_dict()},
        "timestamp": utc_now().isoformat(),
    }


@router.put("/me/password", response_model=dict[str, Any])
async def change_password(
    request: ChangePasswordRequest,
    user: CurrentActiveUser,
) -> dict[str, Any]:
    """修改密码"""
    from ..auth import hash_password, verify_password
    
    # 验证原密码
    if not verify_password(request.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WRONG_PASSWORD", "message": "原密码错误"},
        )
    
    # 更新密码
    manager = get_user_manager()
    new_hash = hash_password(request.new_password)
    await manager.update_user(user.user_id, password_hash=new_hash)
    
    logger.info(f"密码已修改: {user.user_id}")
    
    return {
        "success": True,
        "data": {"message": "密码已修改"},
        "timestamp": utc_now().isoformat(),
    }


# ========================================
# 交易所配置接口
# ========================================

@router.get("/me/exchange", response_model=dict[str, Any])
async def get_exchange_config(user: CurrentActiveUser) -> dict[str, Any]:
    """获取交易所配置"""
    manager = get_user_manager()
    config = await manager.get_exchange_config(user.user_id)
    
    if not config:
        return {
            "success": True,
            "data": {"config": None, "message": "未配置交易所"},
            "timestamp": utc_now().isoformat(),
        }
    
    return {
        "success": True,
        "data": {"config": config.to_dict(include_keys=True)},
        "timestamp": utc_now().isoformat(),
    }


@router.put("/me/exchange", response_model=dict[str, Any])
async def set_exchange_config(
    request: ExchangeConfigRequest,
    user: CurrentActiveUser,
) -> dict[str, Any]:
    """设置交易所配置"""
    manager = get_user_manager()
    
    config = await manager.set_exchange_config(
        user_id=user.user_id,
        api_key=request.api_key,
        api_secret=request.api_secret,
        testnet=request.testnet,
        leverage=request.leverage,
        max_position_pct=request.max_position_pct,
    )
    
    logger.info(f"交易所配置已更新: {user.user_id}")
    
    return {
        "success": True,
        "data": {
            "config": config.to_dict(include_keys=True),
            "message": "配置已保存，请验证 API Key",
        },
        "timestamp": utc_now().isoformat(),
    }


@router.post("/me/exchange/verify", response_model=dict[str, Any])
async def verify_exchange_config(user: CurrentActiveUser) -> dict[str, Any]:
    """验证交易所 API Key"""
    manager = get_user_manager()
    
    is_valid, error = await manager.verify_api_key(user.user_id)
    
    if not is_valid:
        return {
            "success": False,
            "data": {"is_valid": False, "error": error},
            "timestamp": utc_now().isoformat(),
        }
    
    return {
        "success": True,
        "data": {"is_valid": True, "message": "API Key 验证成功"},
        "timestamp": utc_now().isoformat(),
    }


@router.delete("/me/exchange", response_model=dict[str, Any])
async def delete_exchange_config(user: CurrentActiveUser) -> dict[str, Any]:
    """删除交易所配置"""
    manager = get_user_manager()
    deleted = await manager.delete_exchange_config(user.user_id)
    
    return {
        "success": deleted,
        "data": {"message": "配置已删除" if deleted else "配置不存在"},
        "timestamp": utc_now().isoformat(),
    }


# ========================================
# 交易数据接口
# ========================================

@router.get("/me/positions", response_model=dict[str, Any])
async def get_positions(user: CurrentActiveUser) -> dict[str, Any]:
    """获取当前持仓"""
    manager = get_user_manager()
    
    # 检查交易所配置
    config = await manager.get_exchange_config(user.user_id)
    if not config or not config.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_EXCHANGE", "message": "未配置有效的交易所"},
        )
    
    # 获取解密的 API Key
    keys = manager.get_decrypted_keys(user.user_id)
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "KEY_ERROR", "message": "无法获取 API Key"},
        )
    
    api_key, api_secret = keys
    
    # 创建客户端获取持仓
    from src.core.execution.exchange.binance import BinanceClient
    
    client = BinanceClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=config.testnet,
    )
    
    try:
        await client.connect()
        positions = await client.get_all_positions()
        
        return {
            "success": True,
            "data": {"positions": [p.__dict__ for p in positions]},
            "timestamp": utc_now().isoformat(),
        }
    finally:
        await client.disconnect()


@router.get("/me/orders", response_model=dict[str, Any])
async def get_orders(
    user: CurrentActiveUser,
    symbol: str = "BTCUSDT",
    limit: int = 50,
) -> dict[str, Any]:
    """获取订单历史"""
    manager = get_user_manager()
    
    config = await manager.get_exchange_config(user.user_id)
    if not config or not config.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_EXCHANGE", "message": "未配置有效的交易所"},
        )
    
    keys = manager.get_decrypted_keys(user.user_id)
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "KEY_ERROR", "message": "无法获取 API Key"},
        )
    
    api_key, api_secret = keys
    
    from src.core.execution.exchange.binance import BinanceClient
    
    client = BinanceClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=config.testnet,
    )
    
    try:
        await client.connect()
        orders = await client.get_order_history(symbol=symbol, limit=limit)
        
        return {
            "success": True,
            "data": {"orders": orders, "symbol": symbol},
            "timestamp": utc_now().isoformat(),
        }
    finally:
        await client.disconnect()


@router.get("/me/trades", response_model=dict[str, Any])
async def get_trades(
    user: CurrentActiveUser,
    symbol: str = "BTCUSDT",
    limit: int = 50,
) -> dict[str, Any]:
    """获取成交历史"""
    manager = get_user_manager()
    
    config = await manager.get_exchange_config(user.user_id)
    if not config or not config.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_EXCHANGE", "message": "未配置有效的交易所"},
        )
    
    keys = manager.get_decrypted_keys(user.user_id)
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "KEY_ERROR", "message": "无法获取 API Key"},
        )
    
    api_key, api_secret = keys
    
    from src.core.execution.exchange.binance import BinanceClient
    
    client = BinanceClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=config.testnet,
    )
    
    try:
        await client.connect()
        trades = await client.get_trade_history(symbol=symbol, limit=limit)
        
        return {
            "success": True,
            "data": {"trades": trades, "symbol": symbol},
            "timestamp": utc_now().isoformat(),
        }
    finally:
        await client.disconnect()


@router.get("/me/risk", response_model=dict[str, Any])
async def get_risk_state(user: CurrentActiveUser) -> dict[str, Any]:
    """获取风控状态"""
    manager = get_user_manager()
    risk_state = await manager.get_risk_state(user.user_id)
    
    if not risk_state:
        risk_state = await manager.get_or_create_risk_state(user.user_id)
    
    return {
        "success": True,
        "data": {"risk_state": risk_state.to_dict()},
        "timestamp": utc_now().isoformat(),
    }


@router.get("/me/balance", response_model=dict[str, Any])
async def get_balance(user: CurrentActiveUser) -> dict[str, Any]:
    """获取账户余额"""
    manager = get_user_manager()
    
    config = await manager.get_exchange_config(user.user_id)
    if not config or not config.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_EXCHANGE", "message": "未配置有效的交易所"},
        )
    
    keys = manager.get_decrypted_keys(user.user_id)
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "KEY_ERROR", "message": "无法获取 API Key"},
        )
    
    api_key, api_secret = keys
    
    from src.core.execution.exchange.binance import BinanceClient
    
    client = BinanceClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=config.testnet,
    )
    
    try:
        await client.connect()
        balance = await client.get_balance()
        
        return {
            "success": True,
            "data": {"balance": balance},
            "timestamp": utc_now().isoformat(),
        }
    finally:
        await client.disconnect()
