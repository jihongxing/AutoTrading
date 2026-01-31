"""
执行 API 测试
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.dependencies import init_services
from src.core.execution import ExecutionEngine, ExchangeManager
from src.core.state import StateMachineService
from src.core.risk import RiskControlEngine
from backend.tests.mocks.exchange import MockExchangeClient


@pytest.fixture
def client():
    """测试客户端"""
    mock_client = MockExchangeClient()
    exchange = ExchangeManager(mock_client)
    risk_engine = RiskControlEngine()
    state_service = StateMachineService(risk_engine)
    execution_engine = ExecutionEngine(exchange, state_service, risk_engine)
    init_services(execution_engine=execution_engine)
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """认证头"""
    return {"X-API-Key": "dev-key-001"}


class TestExecutionAPI:
    """执行 API 测试"""
    
    def test_get_orders(self, client, auth_headers):
        """测试获取订单列表"""
        response = client.get("/api/v1/orders", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "orders" in data["data"]
        assert "total" in data["data"]
    
    def test_get_order_not_found(self, client, auth_headers):
        """测试获取不存在的订单"""
        response = client.get(
            "/api/v1/orders/nonexistent",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "ORDER_NOT_FOUND"
    
    def test_get_positions(self, client, auth_headers):
        """测试获取仓位"""
        response = client.get("/api/v1/positions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "positions" in data["data"]
        assert "total_unrealized_pnl" in data["data"]
    
    def test_cancel_order_not_found(self, client, auth_headers):
        """测试撤销不存在的订单"""
        response = client.post(
            "/api/v1/orders/nonexistent/cancel",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
