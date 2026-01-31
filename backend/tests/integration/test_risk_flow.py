"""风控流程集成测试"""

import pytest

from src.common.enums import RiskLevel
from src.core.risk.engine import RiskControlEngine
from src.core.risk.recovery import RecoveryManager
from src.core.risk.base import RiskContext


@pytest.fixture
def engine():
    return RiskControlEngine()


@pytest.fixture
def recovery(engine):
    return RecoveryManager(engine)


class TestRiskFlowIntegration:
    """风控流程集成测试"""
    
    @pytest.mark.asyncio
    async def test_normal_trading_flow(self, engine):
        """正常交易流程"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=1000,
            requested_position=0.02,
        )
        
        result = await engine.check_permission(context)
        assert result.approved is True
        assert engine.current_level == RiskLevel.NORMAL
    
    @pytest.mark.asyncio
    async def test_risk_escalation_flow(self, engine):
        """风险升级流程"""
        # 正常 -> 警告
        context1 = RiskContext(
            equity=83000,
            initial_equity=100000,
            drawdown=0.17,  # 85% of 20%, 超过 80% 阈值
            daily_pnl=-500,
        )
        result1 = await engine.check_permission(context1)
        assert result1.approved is True
        assert engine.current_level == RiskLevel.WARNING
        
        # 警告 -> 冷却
        context2 = RiskContext(
            equity=97000,
            initial_equity=100000,
            drawdown=0.03,
            daily_pnl=-3500,  # 超过 3%
        )
        result2 = await engine.check_permission(context2)
        assert result2.approved is False
        assert engine.current_level == RiskLevel.COOLDOWN
    
    @pytest.mark.asyncio
    async def test_lock_and_recovery_flow(self, engine, recovery):
        """锁定和恢复流程"""
        # 触发锁定
        context = RiskContext(
            equity=75000,
            initial_equity=100000,
            drawdown=0.25,
            daily_pnl=-5000,
        )
        await engine.check_permission(context)
        assert engine.is_locked
        
        # 尝试解锁（时间不足）
        unlock_context = RiskContext(
            equity=90000,
            initial_equity=100000,
            drawdown=0.10,
            daily_pnl=0,
        )
        unlocked = await recovery.request_unlock(unlock_context)
        assert unlocked is False
        assert engine.is_locked
    
    @pytest.mark.asyncio
    async def test_degraded_mode(self, engine, recovery):
        """降级模式测试"""
        # 手动解锁进入降级模式
        await engine.force_lock("测试")
        await recovery.manual_unlock("admin", "测试解锁")
        
        assert not engine.is_locked
        assert recovery.is_degraded
        assert recovery.position_limit_ratio == 0.5
        
        # 仓位调整
        adjusted = recovery.get_adjusted_position(0.04)
        assert adjusted == 0.02
