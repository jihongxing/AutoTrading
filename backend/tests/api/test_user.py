"""
用户 API 测试
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.auth import create_access_token, set_user_manager
from src.user.models import User, UserStatus


class TestUserAPI:
    """用户 API 端点测试"""
    
    @pytest.fixture
    def test_user(self):
        return User(
            user_id="test-user-001",
            email="test@example.com",
            password_hash="hashed",
            status=UserStatus.ACTIVE,
        )
    
    @pytest.fixture
    def mock_user_manager(self, test_user):
        manager = AsyncMock()
        
        async def get_user(user_id):
            if user_id == test_user.user_id:
                return test_user
            return None
        
        manager.get_user = get_user
        manager.get_exchange_config = AsyncMock(return_value=None)
        manager.get_risk_state = AsyncMock(return_value=None)
        return manager
    
    @pytest.fixture
    def client(self, mock_user_manager):
        set_user_manager(mock_user_manager)
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user):
        token = create_access_token(
            user_id=test_user.user_id,
            email=test_user.email,
        )
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_me_unauthorized(self, client):
        response = client.get("/users/me")
        
        assert response.status_code == 401
    
    def test_get_me_with_token(self, client, auth_headers):
        response = client.get("/users/me", headers=auth_headers)
        
        assert response.status_code == 200
    
    def test_update_me_unauthorized(self, client):
        response = client.put(
            "/users/me",
            json={"email": "new@example.com"},
        )
        
        assert response.status_code == 401
    
    def test_change_password_unauthorized(self, client):
        response = client.put(
            "/users/me/password",
            json={
                "old_password": "old",
                "new_password": "new_password_123",
            },
        )
        
        assert response.status_code == 401
    
    def test_get_exchange_unauthorized(self, client):
        response = client.get("/users/me/exchange")
        
        assert response.status_code == 401
    
    def test_set_exchange_validation(self, client, auth_headers):
        # 缺少必填字段
        response = client.put(
            "/users/me/exchange",
            headers=auth_headers,
            json={"api_key": "key"},
        )
        
        assert response.status_code == 422
    
    def test_set_exchange_leverage_validation(self, client, auth_headers):
        # 杠杆超出范围
        response = client.put(
            "/users/me/exchange",
            headers=auth_headers,
            json={
                "api_key": "key",
                "api_secret": "secret",
                "leverage": 200,  # 超过 125
            },
        )
        
        assert response.status_code == 422
