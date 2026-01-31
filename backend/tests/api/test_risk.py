"""
风控 API 测试
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.auth import create_access_token, set_user_manager
from src.api.dependencies import init_services
from src.core.risk import RiskEngine
from src.user.models import User, UserStatus


@pytest.fixture
def test_user():
    """测试用户"""
    return User(
        user_id="test-user-001",
        email="test@example.com",
        password_hash="hashed",
        status=UserStatus.ACTIVE,
    )


@pytest.fixture
def admin_user():
    """管理员用户"""
    return User(
        user_id="admin-user-001",
        email="admin@example.com",
        password_hash="hashed",
        status=UserStatus.ACTIVE,
        is_admin=True,
    )


@pytest.fixture
def mock_user_manager(test_user, admin_user):
    """Mock 用户管理器"""
    manager = AsyncMock()
    
    async def get_user(user_id):
        if user_id == test_user.user_id:
            return test_user
        if user_id == admin_user.user_id:
            return admin_user
        return None
    
    manager.get_user = get_user
    return manager


@pytest.fixture
def client(mock_user_manager):
    """测试客户端"""
    risk_engine = RiskEngine()
    init_services(risk_engine=risk_engine)
    set_user_manager(mock_user_manager)
    return TestClient(app)


@pytest.fixture
def auth_headers(test_user):
    """认证头"""
    token = create_access_token(
        user_id=test_user.user_id,
        email=test_user.email,
        is_admin=False,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    """管理员认证头"""
    token = create_access_token(
        user_id=admin_user.user_id,
        email=admin_user.email,
        is_admin=True,
    )
    return {"Authorization": f"Bearer {token}"}


class TestRiskAPI:
    """风控 API 测试"""
    
    def test_get_risk_status(self, client, auth_headers):
        """测试获取风控状态"""
        response = client.get("/api/v1/risk/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "level" in data["data"]
        assert "is_locked" in data["data"]
    
    def test_get_risk_events(self, client, auth_headers):
        """测试获取风控事件"""
        response = client.get("/api/v1/risk/events", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
    
    def test_unlock_not_locked(self, client, admin_headers):
        """测试解锁未锁定的系统"""
        response = client.post(
            "/api/v1/risk/unlock",
            headers=admin_headers,
            json={"reason": "测试解锁"},
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "NOT_LOCKED"
    
    def test_unlock_requires_admin(self, client, auth_headers):
        """测试解锁需要管理员权限"""
        response = client.post(
            "/api/v1/risk/unlock",
            headers=auth_headers,
            json={"reason": "测试解锁"},
        )
        
        assert response.status_code == 403
