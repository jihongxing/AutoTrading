"""
策略/证人 API 测试
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.auth import create_access_token, set_user_manager
from src.api.dependencies import init_services
from src.common.enums import WitnessTier
from src.strategy import HealthManager, WitnessRegistry
from src.strategy.witnesses import VolatilityReleaseWitness
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
def mock_user_manager(test_user):
    """Mock 用户管理器"""
    manager = AsyncMock()
    
    async def get_user(user_id):
        if user_id == test_user.user_id:
            return test_user
        return None
    
    manager.get_user = get_user
    return manager


@pytest.fixture
def client(mock_user_manager):
    """测试客户端"""
    # 初始化测试服务
    registry = WitnessRegistry()
    health_manager = HealthManager()
    
    # 注册测试证人
    witness = VolatilityReleaseWitness()
    registry.register(witness)
    health_manager.initialize_health(witness)
    
    init_services(
        witness_registry=registry,
        health_manager=health_manager,
    )
    
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


class TestStrategyAPI:
    """策略 API 测试"""
    
    def test_get_all_witnesses(self, client, auth_headers):
        """测试获取所有证人"""
        response = client.get("/api/v1/witnesses", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "witnesses" in data["data"]
        assert "total" in data["data"]
    
    def test_get_witness_detail(self, client, auth_headers):
        """测试获取证人详情"""
        response = client.get(
            "/api/v1/witnesses/volatility_release",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["witness_id"] == "volatility_release"
    
    def test_get_witness_not_found(self, client, auth_headers):
        """测试获取不存在的证人"""
        response = client.get(
            "/api/v1/witnesses/nonexistent",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "WITNESS_NOT_FOUND"
    
    def test_get_witness_health(self, client, auth_headers):
        """测试获取证人健康度"""
        response = client.get(
            "/api/v1/witnesses/volatility_release/health",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "win_rate" in data["data"]
    
    def test_mute_witness(self, client, auth_headers):
        """测试静默证人"""
        response = client.post(
            "/api/v1/witnesses/volatility_release/mute",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_active"] is False
    
    def test_activate_witness(self, client, auth_headers):
        """测试激活证人"""
        # 先静默
        client.post(
            "/api/v1/witnesses/volatility_release/mute",
            headers=auth_headers,
        )
        
        # 再激活
        response = client.post(
            "/api/v1/witnesses/volatility_release/activate",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_active"] is True
