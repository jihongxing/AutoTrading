"""
BTC 自动交易系统 — 执行路由

提供订单和仓位管理接口。
"""

from fastapi import APIRouter, HTTPException, Query, status

from src.api.auth import RequireRead, RequireWrite, audit_log
from src.api.dependencies import ExecutionEngineDep
from src.api.schemas import (
    ApiResponse,
    OrderListResponse,
    OrderResponse,
    PositionListResponse,
    PositionResponse,
)
from src.common.enums import OrderSide, OrderStatus, OrderType

router = APIRouter(prefix="", tags=["执行"])


@router.get("/orders", response_model=ApiResponse[OrderListResponse])
async def get_orders(
    api_key: RequireRead,
    execution_engine: ExecutionEngineDep,
    status_filter: OrderStatus | None = Query(None, alias="status"),
    limit: int = 50,
) -> ApiResponse[OrderListResponse]:
    """
    获取订单列表
    
    返回订单列表，可按状态过滤。
    """
    orders = execution_engine.order_manager.get_all_orders()
    
    # 按状态过滤
    if status_filter:
        orders = [o for o in orders if o.status == status_filter]
    
    order_responses = [
        OrderResponse(
            order_id=o.order_id,
            client_order_id=o.client_order_id,
            symbol=o.symbol,
            side=o.side,
            order_type=o.order_type,
            status=o.status,
            quantity=o.quantity,
            filled_quantity=o.filled_quantity,
            price=o.price,
            avg_price=o.avg_price,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in orders[:limit]
    ]
    
    response = OrderListResponse(
        orders=order_responses,
        total=len(orders),
    )
    
    return ApiResponse(data=response)


@router.get("/orders/{order_id}", response_model=ApiResponse[OrderResponse])
async def get_order(
    order_id: str,
    api_key: RequireRead,
    execution_engine: ExecutionEngineDep,
) -> ApiResponse[OrderResponse]:
    """
    获取订单详情
    
    返回指定订单的详细信息。
    """
    order = execution_engine.order_manager.get_order(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORDER_NOT_FOUND", "message": f"订单不存在: {order_id}"},
        )
    
    response = OrderResponse(
        order_id=order.order_id,
        client_order_id=order.client_order_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        status=order.status,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        price=order.price,
        avg_price=order.avg_price,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
    
    return ApiResponse(data=response)


@router.post("/orders/{order_id}/cancel", response_model=ApiResponse[OrderResponse])
async def cancel_order(
    order_id: str,
    api_key: RequireWrite,
    execution_engine: ExecutionEngineDep,
) -> ApiResponse[OrderResponse]:
    """
    撤销订单
    
    撤销指定的未完成订单。
    """
    order = execution_engine.order_manager.get_order(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORDER_NOT_FOUND", "message": f"订单不存在: {order_id}"},
        )
    
    if order.status not in (OrderStatus.PENDING, OrderStatus.OPEN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CANNOT_CANCEL", "message": f"订单状态不允许撤销: {order.status}"},
        )
    
    audit_log.log(
        api_key=api_key.key,
        action="cancel_order",
        resource=order_id,
    )
    
    try:
        execution_engine.order_manager.cancel_order(order_id)
        
        # 重新获取更新后的订单
        updated_order = execution_engine.order_manager.get_order(order_id)
        
        response = OrderResponse(
            order_id=updated_order.order_id,
            client_order_id=updated_order.client_order_id,
            symbol=updated_order.symbol,
            side=updated_order.side,
            order_type=updated_order.order_type,
            status=updated_order.status,
            quantity=updated_order.quantity,
            filled_quantity=updated_order.filled_quantity,
            price=updated_order.price,
            avg_price=updated_order.avg_price,
            created_at=updated_order.created_at,
            updated_at=updated_order.updated_at,
        )
        
        return ApiResponse(data=response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CANCEL_FAILED", "message": str(e)},
        )


@router.get("/positions", response_model=ApiResponse[PositionListResponse])
async def get_positions(
    api_key: RequireRead,
    execution_engine: ExecutionEngineDep,
) -> ApiResponse[PositionListResponse]:
    """
    获取当前仓位
    
    返回所有当前持仓。
    """
    positions = execution_engine.position_manager.get_all_positions()
    
    position_responses = []
    total_pnl = 0.0
    
    for p in positions:
        unrealized_pnl = p.unrealized_pnl
        total_pnl += unrealized_pnl
        
        position_responses.append(PositionResponse(
            symbol=p.symbol,
            side=p.side,
            quantity=p.quantity,
            entry_price=p.entry_price,
            current_price=p.current_price,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=p.unrealized_pnl_pct,
            leverage=p.leverage,
            liquidation_price=p.liquidation_price,
        ))
    
    response = PositionListResponse(
        positions=position_responses,
        total_unrealized_pnl=total_pnl,
    )
    
    return ApiResponse(data=response)
