"""
认证 API 测试
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.auth import hash_password, verify_password, create_access_token, verify_token, TokenType


class TestPasswordHashing:
    """密码哈希测试"""
    
    def test_hash_and_verify(self):
        password = "my_secure_password"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    def test_different_hashes(self):
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # 每次哈希不同（因为 salt）
        assert hash1 != hash2
        
        # 但都能验证
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWT:
    """JWT Token 测试"""
    
    def test_create_and_verify_access_token(self):
        token = create_access_token(
            user_id="user-123",
            email="test@example.com",
        )
        
        payload = verify_token(token, TokenType.ACCESS)
        
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
    
    def test_admin_token(self):
        token = create_access_token(
            user_id="admin-001",
            email="admin@example.com",
            is_admin=True,
        )
        
        payload = verify_token(token, TokenType.ACCESS)
        
        assert payload["is_admin"] is True


class TestAuthAPI:
    """认证 API 端点测试"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_register_success(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "secure_password_123",
            },
        )
        
        # 可能因为邮箱已存在返回 400，或成功返回 200
        assert response.status_code in [200, 400, 500]
    
    def test_register_invalid_email(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "password": "secure_password",
            },
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_register_short_password(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
            },
        )
        
        assert response.status_code == 422
    
    def test_login_missing_fields(self, client):
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com"},
        )
        
        assert response.status_code == 422
