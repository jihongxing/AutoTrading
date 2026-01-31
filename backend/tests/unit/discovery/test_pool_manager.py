"""
假设候选池管理器测试
"""

import pytest

from src.common.enums import HypothesisStatus
from src.discovery.pool.manager import HypothesisPoolManager, MAX_HYPOTHESES
from src.discovery.pool.models import Hypothesis


@pytest.fixture
def pool_manager():
    """创建候选池管理器"""
    return HypothesisPoolManager(max_size=10)


@pytest.fixture
def sample_hypothesis():
    """创建示例假设"""
    return Hypothesis(
        id="hyp_test_001",
        name="测试假设",
        status=HypothesisStatus.NEW,
        source_detector="volatility",
        source_event="event_001",
        event_definition="test",
        event_params={},
        expected_direction="long",
        expected_win_rate=(0.52, 0.55),
    )


class TestHypothesisPoolManager:
    """候选池管理器测试"""
    
    @pytest.mark.asyncio
    async def test_add_hypothesis(self, pool_manager, sample_hypothesis):
        """测试添加假设"""
        result = await pool_manager.add(sample_hypothesis)
        
        assert result is True
        assert pool_manager.count == 1
    
    @pytest.mark.asyncio
    async def test_add_duplicate(self, pool_manager, sample_hypothesis):
        """测试添加重复假设"""
        await pool_manager.add(sample_hypothesis)
        result = await pool_manager.add(sample_hypothesis)
        
        assert result is False
        assert pool_manager.count == 1

    @pytest.mark.asyncio
    async def test_capacity_limit(self, pool_manager):
        """测试容量限制"""
        for i in range(10):
            h = Hypothesis(
                id=f"hyp_{i}",
                name=f"假设{i}",
                status=HypothesisStatus.NEW,
                source_detector="volatility",
                source_event=f"event_{i}",
                event_definition="test",
                event_params={},
                expected_direction="long",
                expected_win_rate=(0.52, 0.55),
            )
            await pool_manager.add(h)
        
        # 第 11 个应该失败
        h11 = Hypothesis(
            id="hyp_10",
            name="假设10",
            status=HypothesisStatus.NEW,
            source_detector="volatility",
            source_event="event_10",
            event_definition="test",
            event_params={},
            expected_direction="long",
            expected_win_rate=(0.52, 0.55),
        )
        result = await pool_manager.add(h11)
        
        assert result is False
        assert pool_manager.count == 10
    
    @pytest.mark.asyncio
    async def test_get_hypothesis(self, pool_manager, sample_hypothesis):
        """测试获取假设"""
        await pool_manager.add(sample_hypothesis)
        
        h = await pool_manager.get("hyp_test_001")
        assert h is not None
        assert h.id == "hyp_test_001"
        
        h_none = await pool_manager.get("nonexistent")
        assert h_none is None
    
    @pytest.mark.asyncio
    async def test_update_status(self, pool_manager, sample_hypothesis):
        """测试更新状态"""
        await pool_manager.add(sample_hypothesis)
        
        result = await pool_manager.update_status("hyp_test_001", HypothesisStatus.TIER_1)
        assert result is True
        
        h = await pool_manager.get("hyp_test_001")
        assert h.status == HypothesisStatus.TIER_1
    
    @pytest.mark.asyncio
    async def test_get_by_status(self, pool_manager):
        """测试按状态获取"""
        for i, status in enumerate([HypothesisStatus.NEW, HypothesisStatus.TIER_1, HypothesisStatus.NEW]):
            h = Hypothesis(
                id=f"hyp_{i}",
                name=f"假设{i}",
                status=status,
                source_detector="volatility",
                source_event=f"event_{i}",
                event_definition="test",
                event_params={},
                expected_direction="long",
                expected_win_rate=(0.52, 0.55),
            )
            await pool_manager.add(h)
        
        new_list = await pool_manager.get_by_status(HypothesisStatus.NEW)
        assert len(new_list) == 2
        
        tier1_list = await pool_manager.get_by_status(HypothesisStatus.TIER_1)
        assert len(tier1_list) == 1
    
    @pytest.mark.asyncio
    async def test_get_promotable(self, pool_manager):
        """测试获取可晋升假设"""
        statuses = [HypothesisStatus.TIER_1, HypothesisStatus.TIER_2, HypothesisStatus.FAIL]
        for i, status in enumerate(statuses):
            h = Hypothesis(
                id=f"hyp_{i}",
                name=f"假设{i}",
                status=status,
                source_detector="volatility",
                source_event=f"event_{i}",
                event_definition="test",
                event_params={},
                expected_direction="long",
                expected_win_rate=(0.52, 0.55),
            )
            await pool_manager.add(h)
        
        promotable = await pool_manager.get_promotable()
        assert len(promotable) == 2
    
    @pytest.mark.asyncio
    async def test_remove(self, pool_manager, sample_hypothesis):
        """测试移除假设"""
        await pool_manager.add(sample_hypothesis)
        assert pool_manager.count == 1
        
        result = await pool_manager.remove("hyp_test_001")
        assert result is True
        assert pool_manager.count == 0
    
    def test_statistics(self, pool_manager):
        """测试统计信息"""
        stats = pool_manager.get_statistics()
        assert stats["total"] == 0
