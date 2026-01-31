"""
策略生命周期集成测试

测试完整生命周期流程：NEW → TESTING → SHADOW → ACTIVE → DEGRADED → RETIRED
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.common.enums import (
    ClaimType,
    HealthGrade,
    HypothesisStatus,
    StrategyStatus,
    WitnessStatus,
    WitnessTier,
)
from src.common.models import Claim, WitnessHealth
from src.discovery.pool.manager import HypothesisPoolManager
from src.discovery.pool.models import Hypothesis
from src.strategy.health import HealthManager
from src.strategy.lifecycle.manager import StrategyPoolManager
from src.strategy.lifecycle.shadow import ShadowRunner
from src.strategy.lifecycle.weight import WeightManager
from src.strategy.registry import WitnessRegistry


def make_claim(strategy_id: str, direction: str = "long") -> Claim:
    """创建测试用 Claim"""
    return Claim(
        strategy_id=strategy_id,
        claim_type=ClaimType.MARKET_ELIGIBLE,
        confidence=0.7,
        validity_window=300,
        direction=direction,
    )


@pytest.fixture
def hypothesis_pool():
    return HypothesisPoolManager()


@pytest.fixture
def registry():
    return WitnessRegistry()


@pytest.fixture
def health_manager():
    return HealthManager()


@pytest.fixture
def weight_manager(health_manager):
    return WeightManager(health_manager=health_manager)


@pytest.fixture
def pool_manager(hypothesis_pool, registry, health_manager, weight_manager):
    return StrategyPoolManager(
        hypothesis_pool=hypothesis_pool,
        registry=registry,
        health_manager=health_manager,
        weight_manager=weight_manager,
    )


@pytest.fixture
def shadow_runner():
    return ShadowRunner()


class TestLifecycleFlow:
    """完整生命周期流程测试"""
    
    @pytest.mark.asyncio
    async def test_hypothesis_to_shadow_flow(self, hypothesis_pool):
        """假设 → SHADOW 流程"""
        # 创建假设
        hypothesis = Hypothesis(
            id="test_hypo_1",
            name="测试假设",
            status=HypothesisStatus.NEW,
            source_detector="volatility",
            source_event="vol_compression_001",
            event_definition="volatility < threshold",
            event_params={"threshold": 0.5},
            expected_direction="long",
            expected_win_rate=(0.51, 0.55),
        )
        
        # 添加到候选池
        added = await hypothesis_pool.add(hypothesis)
        assert added is True
        
        # 验证通过后晋升到 TIER_1
        await hypothesis_pool.update_status("test_hypo_1", HypothesisStatus.TIER_1)
        
        # 晋升到 SHADOW
        promoted = await hypothesis_pool.promote_to_shadow("test_hypo_1")
        assert promoted is True
        
        # 验证在 SHADOW 池中
        shadow_list = await hypothesis_pool.get_shadow_hypotheses()
        assert len(shadow_list) == 1
        assert shadow_list[0].id == "test_hypo_1"
    
    @pytest.mark.asyncio
    async def test_shadow_performance_tracking(self, shadow_runner):
        """影子运行绩效跟踪"""
        # 注册影子策略
        mock_strategy = MagicMock()
        mock_strategy.strategy_id = "shadow_test"
        mock_strategy.run.return_value = make_claim("shadow_test")
        
        shadow_runner.register_strategy(mock_strategy)
        
        # 模拟多笔交易
        for i in range(5):
            claim = make_claim("shadow_test")
            shadow_runner._record_trade("shadow_test", claim, 50000.0 + i * 100)
            # 模拟盈利交易
            shadow_runner.update_trade_result("shadow_test", 50100.0 + i * 100)
        
        # 检查绩效
        perf = shadow_runner.get_performance("shadow_test")
        assert perf is not None
        assert perf.total_trades == 5
        assert perf.winning_trades == 5
        assert perf.win_rate == 1.0
    
    @pytest.mark.asyncio
    async def test_weight_health_integration(self, health_manager, weight_manager, registry):
        """权重与健康度联动"""
        # 创建模拟证人
        mock_witness = MagicMock()
        mock_witness.strategy_id = "weight_test"
        mock_witness.tier = WitnessTier.TIER_2
        mock_witness.is_active = True
        
        # 注册证人
        registry.register(mock_witness)
        
        # 初始化健康度
        health_manager.initialize_health(mock_witness)
        
        # 获取初始权重
        weight = weight_manager.get_weight("weight_test")
        initial_effective = weight.effective_weight
        
        # 模拟健康度变化 - 多次盈利交易提升到 A 级
        from src.strategy.health import TradeResult
        from src.common.utils import utc_now
        
        for i in range(60):
            result = TradeResult(
                strategy_id="weight_test",
                is_win=True,
                pnl=0.01,
                timestamp=utc_now(),
            )
            health_manager.update_health("weight_test", result)
        
        # 获取更新后的权重
        updated_weight = weight_manager.get_weight("weight_test")
        
        # 健康度 A 应该有 1.2 的 health_factor
        health = health_manager.get_health("weight_test")
        assert health.grade == HealthGrade.A
        assert updated_weight.health_factor == 1.2
        assert updated_weight.effective_weight > initial_effective


class TestDemotionFlow:
    """降级流程测试"""
    
    @pytest.mark.asyncio
    async def test_auto_demotion_on_poor_health(self, pool_manager, registry, health_manager):
        """健康度差自动降级"""
        # 创建并注册证人
        mock_witness = MagicMock()
        mock_witness.strategy_id = "demote_test"
        mock_witness.tier = WitnessTier.TIER_2
        mock_witness.is_active = True
        
        registry.register(mock_witness)
        health_manager.initialize_health(mock_witness)
        
        # 模拟连续亏损导致健康度下降到 D
        from src.strategy.health import TradeResult
        from src.common.utils import utc_now
        
        for i in range(60):
            result = TradeResult(
                strategy_id="demote_test",
                is_win=False,
                pnl=-0.01,
                timestamp=utc_now(),
            )
            health_manager.update_health("demote_test", result)
        
        # 检查健康度
        health = health_manager.get_health("demote_test")
        assert health.grade == HealthGrade.D
        
        # 执行自动降级检查
        demoted = await pool_manager.check_demotions()
        assert "demote_test" in demoted
        
        # 验证状态变更
        status = registry.get_status("demote_test")
        assert status == StrategyStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_protected_strategy_not_demoted(self, pool_manager, registry):
        """受保护策略不被降级"""
        # 创建 TIER_3 证人
        mock_witness = MagicMock()
        mock_witness.strategy_id = "risk_sentinel"
        mock_witness.tier = WitnessTier.TIER_3
        mock_witness.is_active = True
        
        registry.register(mock_witness)
        
        # 尝试降级
        result = await pool_manager.demote("risk_sentinel")
        assert result is False
        
        # 状态应保持 ACTIVE
        status = registry.get_status("risk_sentinel")
        assert status == StrategyStatus.ACTIVE


class TestTierUpgradeFlow:
    """TIER 升级流程测试"""
    
    @pytest.mark.asyncio
    async def test_tier2_to_tier1_upgrade(self, pool_manager, registry, health_manager):
        """TIER_2 升级到 TIER_1"""
        # 创建 TIER_2 证人
        mock_witness = MagicMock()
        mock_witness.strategy_id = "upgrade_test"
        mock_witness.tier = WitnessTier.TIER_2
        mock_witness.is_active = True
        
        registry.register(mock_witness)
        health_manager.initialize_health(mock_witness)
        
        # 模拟优秀表现达到 A 级
        from src.strategy.health import TradeResult
        from src.common.utils import utc_now
        
        for i in range(60):
            result = TradeResult(
                strategy_id="upgrade_test",
                is_win=True,
                pnl=0.01,
                timestamp=utc_now(),
            )
            health_manager.update_health("upgrade_test", result)
        
        # 验证健康度 A
        health = health_manager.get_health("upgrade_test")
        assert health.grade == HealthGrade.A
        
        # 执行升级
        upgraded = await pool_manager.upgrade_tier("upgrade_test", by="admin")
        assert upgraded is True
        
        # 验证 TIER 变更
        tier = registry.get_tier("upgrade_test")
        assert tier == WitnessTier.TIER_1
    
    @pytest.mark.asyncio
    async def test_tier_upgrade_requires_grade_a(self, pool_manager, registry, health_manager):
        """升级需要健康度 A"""
        # 创建 TIER_2 证人
        mock_witness = MagicMock()
        mock_witness.strategy_id = "upgrade_fail_test"
        mock_witness.tier = WitnessTier.TIER_2
        mock_witness.is_active = True
        
        registry.register(mock_witness)
        health_manager.initialize_health(mock_witness)
        
        # 健康度保持 B（默认）
        health = health_manager.get_health("upgrade_fail_test")
        assert health.grade == HealthGrade.B
        
        # 尝试升级应失败
        upgraded = await pool_manager.upgrade_tier("upgrade_fail_test")
        assert upgraded is False


class TestWeightOptimization:
    """权重优化测试"""
    
    def test_learning_factor_bounds(self, weight_manager):
        """学习因子边界限制"""
        # 设置超出上限
        weight_manager.set_learning_factor("test", 1.5)
        weight = weight_manager.get_weight("test")
        assert weight.learning_factor == 1.2  # 上限
        
        # 设置超出下限
        weight_manager.set_learning_factor("test", 0.5)
        weight = weight_manager.get_weight("test")
        assert weight.learning_factor == 0.8  # 下限
    
    def test_base_weight_bounds(self, weight_manager):
        """基础权重边界限制"""
        # 设置超出上限
        weight_manager.set_base_weight("test", 3.0)
        weight = weight_manager.get_weight("test")
        assert weight.base_weight == 2.0  # 上限
        
        # 设置超出下限
        weight_manager.set_base_weight("test", 0.1)
        weight = weight_manager.get_weight("test")
        assert weight.base_weight == 0.5  # 下限
    
    def test_effective_weight_calculation(self, weight_manager):
        """有效权重计算"""
        weight_manager.set_base_weight("calc_test", 1.5)
        weight_manager.set_learning_factor("calc_test", 1.1)
        
        weight = weight_manager.get_weight("calc_test")
        
        # effective = base * health * learning
        # health 默认 1.0
        expected = 1.5 * 1.0 * 1.1
        assert abs(weight.effective_weight - expected) < 0.001


class TestRegistryExtensions:
    """Registry 扩展功能测试"""
    
    def test_status_management(self, registry):
        """状态管理"""
        mock_witness = MagicMock()
        mock_witness.strategy_id = "status_test"
        mock_witness.tier = WitnessTier.TIER_2
        mock_witness.is_active = True
        
        registry.register(mock_witness)
        
        # 初始状态
        assert registry.get_status("status_test") == StrategyStatus.ACTIVE
        
        # 修改状态
        registry.set_status("status_test", StrategyStatus.DEGRADED)
        assert registry.get_status("status_test") == StrategyStatus.DEGRADED
    
    def test_tier_override(self, registry):
        """TIER 动态覆盖"""
        mock_witness = MagicMock()
        mock_witness.strategy_id = "tier_test"
        mock_witness.tier = WitnessTier.TIER_2
        mock_witness.is_active = True
        
        registry.register(mock_witness)
        
        # 初始 TIER
        assert registry.get_tier("tier_test") == WitnessTier.TIER_2
        
        # 覆盖 TIER
        registry.set_tier("tier_test", WitnessTier.TIER_1)
        assert registry.get_tier("tier_test") == WitnessTier.TIER_1
    
    def test_protected_witness_tier_immutable(self, registry):
        """受保护证人 TIER 不可修改"""
        mock_witness = MagicMock()
        mock_witness.strategy_id = "protected_test"
        mock_witness.tier = WitnessTier.TIER_3
        mock_witness.is_active = True
        
        registry.register(mock_witness)
        
        # 尝试修改应失败
        result = registry.set_tier("protected_test", WitnessTier.TIER_2)
        assert result is False
        
        # TIER 保持不变
        assert registry.get_tier("protected_test") == WitnessTier.TIER_3
