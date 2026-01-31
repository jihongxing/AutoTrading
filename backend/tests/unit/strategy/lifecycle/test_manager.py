"""
策略池管理器测试
"""

import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.common.enums import HealthGrade, HypothesisStatus, StrategyStatus, WitnessStatus, WitnessTier
from src.common.models import WitnessHealth
from src.strategy.lifecycle.manager import StrategyPoolManager
from src.strategy.lifecycle.storage import LifecycleStorage


@pytest.fixture
def mock_hypothesis_pool():
    pool = MagicMock()
    pool.get = AsyncMock(return_value=None)
    pool.update_status = AsyncMock(return_value=True)
    pool.promote_to_shadow = AsyncMock(return_value=True)
    pool.remove_from_shadow = AsyncMock(return_value=True)
    return pool


@pytest.fixture
def mock_registry():
    registry = MagicMock()
    registry.get_status.return_value = None
    registry.set_status.return_value = True
    registry.get_tier.return_value = WitnessTier.TIER_2
    registry.set_tier.return_value = True
    registry.is_protected.return_value = False
    registry.get_witness.return_value = None
    registry.get_by_status.return_value = []
    return registry


@pytest.fixture
def mock_health_manager():
    manager = MagicMock()
    manager.get_health.return_value = None
    return manager


@pytest.fixture
def mock_weight_manager():
    manager = MagicMock()
    return manager


@pytest.fixture
def temp_storage():
    """使用临时目录的存储"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LifecycleStorage(data_dir=tmpdir)


@pytest.fixture
def pool_manager(mock_hypothesis_pool, mock_registry, mock_health_manager, mock_weight_manager, temp_storage):
    return StrategyPoolManager(
        hypothesis_pool=mock_hypothesis_pool,
        registry=mock_registry,
        health_manager=mock_health_manager,
        weight_manager=mock_weight_manager,
        storage=temp_storage,
    )


class TestStrategyPoolManager:
    """StrategyPoolManager 测试"""
    
    def test_get_status_from_registry(self, pool_manager, mock_registry):
        """从 registry 获取状态"""
        mock_registry.get_status.return_value = StrategyStatus.ACTIVE
        status = pool_manager.get_status("test")
        assert status == StrategyStatus.ACTIVE
    
    def test_get_all_by_status(self, pool_manager, mock_registry):
        """按状态获取策略"""
        mock_witness = MagicMock()
        mock_witness.strategy_id = "test"
        mock_registry.get_by_status.return_value = [mock_witness]
        
        result = pool_manager.get_all_by_status(StrategyStatus.ACTIVE)
        assert "test" in result
    
    def test_get_state_history(self, pool_manager):
        """获取状态历史"""
        history = pool_manager.get_state_history("test")
        assert history == []


class TestPromotionLogic:
    """晋升逻辑测试"""
    
    @pytest.mark.asyncio
    async def test_promote_protected_strategy(self, pool_manager, mock_registry):
        """受保护策略不可降级"""
        mock_registry.is_protected.return_value = True
        mock_registry.get_status.return_value = StrategyStatus.ACTIVE
        
        result = await pool_manager.demote("protected_strategy")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_upgrade_tier_requires_tier2(self, pool_manager, mock_registry, mock_health_manager):
        """升级 TIER 需要当前是 TIER_2"""
        mock_witness = MagicMock()
        mock_registry.get_witness.return_value = mock_witness
        mock_registry.get_tier.return_value = WitnessTier.TIER_1
        
        result = await pool_manager.upgrade_tier("test")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_upgrade_tier_requires_grade_a(self, pool_manager, mock_registry, mock_health_manager):
        """升级 TIER 需要健康度 A"""
        mock_witness = MagicMock()
        mock_registry.get_witness.return_value = mock_witness
        mock_registry.get_tier.return_value = WitnessTier.TIER_2
        
        mock_health_manager.get_health.return_value = WitnessHealth(
            witness_id="test",
            tier=WitnessTier.TIER_2,
            status=WitnessStatus.ACTIVE,
            grade=HealthGrade.B,
            win_rate=0.53,
            sample_count=100,
            weight=0.5,
        )
        
        result = await pool_manager.upgrade_tier("test")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_upgrade_tier_success(self, pool_manager, mock_registry, mock_health_manager):
        """成功升级 TIER"""
        mock_witness = MagicMock()
        mock_registry.get_witness.return_value = mock_witness
        mock_registry.get_tier.return_value = WitnessTier.TIER_2
        
        mock_health_manager.get_health.return_value = WitnessHealth(
            witness_id="test",
            tier=WitnessTier.TIER_2,
            status=WitnessStatus.ACTIVE,
            grade=HealthGrade.A,
            win_rate=0.56,
            sample_count=100,
            weight=0.5,
        )
        
        result = await pool_manager.upgrade_tier("test")
        assert result is True
        mock_registry.set_tier.assert_called_once_with("test", WitnessTier.TIER_1)


class TestDemotionLogic:
    """降级逻辑测试"""
    
    @pytest.mark.asyncio
    async def test_demote_active_strategy(self, pool_manager, mock_registry):
        """降级 ACTIVE 策略"""
        mock_registry.get_status.return_value = StrategyStatus.ACTIVE
        mock_registry.is_protected.return_value = False
        
        result = await pool_manager.demote("test")
        assert result is True
        mock_registry.set_status.assert_called_once_with("test", StrategyStatus.DEGRADED)
    
    @pytest.mark.asyncio
    async def test_retire_degraded_strategy(self, pool_manager, mock_registry):
        """废弃 DEGRADED 策略"""
        mock_registry.get_status.return_value = StrategyStatus.DEGRADED
        mock_registry.is_protected.return_value = False
        
        result = await pool_manager.retire("test")
        assert result is True
        mock_registry.set_status.assert_called_once_with("test", StrategyStatus.RETIRED)
    
    @pytest.mark.asyncio
    async def test_check_demotions(self, pool_manager, mock_registry, mock_health_manager):
        """自动降级检查"""
        mock_witness = MagicMock()
        mock_witness.strategy_id = "unhealthy"
        mock_registry.get_by_status.return_value = [mock_witness]
        mock_registry.get_status.return_value = StrategyStatus.ACTIVE
        mock_registry.is_protected.return_value = False
        
        mock_health_manager.get_health.return_value = WitnessHealth(
            witness_id="unhealthy",
            tier=WitnessTier.TIER_2,
            status=WitnessStatus.ACTIVE,
            grade=HealthGrade.D,
            win_rate=0.25,
            sample_count=100,
            weight=0.5,
        )
        
        demoted = await pool_manager.check_demotions()
        assert "unhealthy" in demoted
