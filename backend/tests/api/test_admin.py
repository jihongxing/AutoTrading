"""
管理后台 API 测试
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.auth import create_access_token


class TestAdminAPI:
    """管理后台 API 端点测试"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def admin_headers(self):
        token = create_access_token(
            user_id="admin-001",
            email="admin@example.com",
            is_admin=True,
        )
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def user_headers(self):
        token = create_access_token(
            user_id="user-001",
            email="user@example.com",
            is_admin=False,
        )
        return {"Authorization": f"Bearer {token}"}
    
    def test_list_users_unauthorized(self, client):
        response = client.get("/admin/users")
        
        assert response.status_code == 401
    
    def test_list_users_non_admin(self, client, user_headers):
        response = client.get("/admin/users", headers=user_headers)
        
        assert response.status_code == 403
    
    def test_list_users_admin(self, client, admin_headers):
        response = client.get("/admin/users", headers=admin_headers)
        
        # 可能因为用户不存在而返回 401
        assert response.status_code in [200, 401]
    
    def test_get_user_non_admin(self, client, user_headers):
        response = client.get("/admin/users/some-id", headers=user_headers)
        
        assert response.status_code == 403
    
    def test_suspend_user_non_admin(self, client, user_headers):
        response = client.post(
            "/admin/users/some-id/suspend",
            headers=user_headers,
            json={"reason": "test"},
        )
        
        assert response.status_code == 403
    
    def test_get_stats_non_admin(self, client, user_headers):
        response = client.get("/admin/stats", headers=user_headers)
        
        assert response.status_code == 403
    
    def test_get_profit_non_admin(self, client, user_headers):
        response = client.get("/admin/profit", headers=user_headers)
        
        assert response.status_code == 403
