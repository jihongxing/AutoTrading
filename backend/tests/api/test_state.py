"""
系统状态 API 测试
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.auth import create_access_token, set_user_manager
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


class TestStateAPI:
    """系统状态 API 测试"""
    
    def test_get_current_state(self, client, auth_headers):
        """测试获取当前状态"""
        response = client.get("/api/v1/state", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "current_state" in data["data"]
        assert "is_trading_allowed" in data["data"]
    
    def test_get_current_state_no_auth(self, client):
        """测试无认证获取状态"""
        response = client.get("/api/v1/state")
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "MISSING_TOKEN"
    
    def test_get_current_state_invalid_key(self, client):
        """测试无效 Token"""
        response = client.get("/api/v1/state", headers={"Authorization": "Bearer invalid"})
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"
    
    def test_get_state_history(self, client, auth_headers):
        """测试获取状态历史"""
        response = client.get("/api/v1/state/history", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert "total" in data["data"]
    
    def test_force_lock_requires_admin(self, client, auth_headers):
        """测试强制锁定需要管理员权限"""
        response = client.post(
            "/api/v1/state/force-lock",
            headers=auth_headers,
            json={"reason": "测试锁定"},
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "ADMIN_REQUIRED"
    
    def test_force_lock_with_admin(self, client, admin_headers):
        """测试管理员强制锁定"""
        response = client.post(
            "/api/v1/state/force-lock",
            headers=admin_headers,
            json={"reason": "测试锁定"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
