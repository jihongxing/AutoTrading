"""风控引擎测试"""

import pytest

from src.common.enums import RiskLevel
from src.core.risk.engine import RiskControlEngine
from src.core.risk.base import RiskContext


@pytest.fixture
def engine():
    return RiskControlEngine()


@pytest.fixture
def normal_context():
    return RiskContext(
        equity=100000,
        initial_equity=100000,
        drawdown=0.05,
        daily_pnl=500,
    )


class TestRiskControlEngine:
    """风控引擎测试"""
    
    def test_init(self, engine):
        """测试初始化"""
        assert engine.current_level == RiskLevel.NORMAL
        assert not engine.is_locked
        assert not engine.is_cooldown
        assert len(engine._checkers) == 5
    
    @pytest.mark.asyncio
    async def test_normal_approve(self, engine, normal_context):
        """正常情况批准"""
        result = await engine.check_permission(normal_context)
        assert result.approved is True
    
    @pytest.mark.asyncio
    async def test_drawdown_lock(self, engine):
        """回撤超限锁定"""
        context = RiskContext(
            equity=75000,
            initial_equity=100000,
            drawdown=0.25,
            daily_pnl=-5000,
        )
        result = await engine.check_permission(context)
        assert result.approved is False
        assert result.level == RiskLevel.RISK_LOCKED
        assert engine.is_locked
    
    @pytest.mark.asyncio
    async def test_locked_reject(self, engine, normal_context):
        """锁定状态拒绝"""
        await engine.force_lock("测试锁定")
        assert engine.is_locked
        
        result = await engine.check_permission(normal_context)
        assert result.approved is False
        assert "锁定" in result.reason
    
    @pytest.mark.asyncio
    async def test_force_cooldown(self, engine, normal_context):
        """强制冷却"""
        await engine.force_cooldown("测试冷却")
        assert engine.is_cooldown
        assert engine.current_level == RiskLevel.COOLDOWN
    
    def test_add_remove_checker(self, engine):
        """添加和移除检查器"""
        initial_count = len(engine._checkers)
        
        # 移除
        engine.remove_checker("account_risk")
        assert len(engine._checkers) == initial_count - 1
        
        # 添加
        from src.core.risk.account_risk import AccountRiskChecker
        engine.add_checker(AccountRiskChecker())
        assert len(engine._checkers) == initial_count
    
    def test_reset_to_normal(self, engine):
        """重置状态"""
        engine._current_level = RiskLevel.RISK_LOCKED
        engine._lock_reason = "测试"
        
        engine.reset_to_normal()
        
        assert engine.current_level == RiskLevel.NORMAL
        assert engine._lock_reason is None


class TestRiskLevelPriority:
    """风险级别优先级测试"""
    
    def test_level_priority(self, engine):
        """测试级别优先级"""
        assert engine._level_priority(RiskLevel.NORMAL) == 0
        assert engine._level_priority(RiskLevel.WARNING) == 1
        assert engine._level_priority(RiskLevel.COOLDOWN) == 2
        assert engine._level_priority(RiskLevel.RISK_LOCKED) == 3
