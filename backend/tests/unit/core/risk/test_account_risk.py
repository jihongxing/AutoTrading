"""账户风控测试"""

import pytest

from src.common.enums import RiskLevel
from src.core.risk.account_risk import AccountRiskChecker
from src.core.risk.base import RiskContext


@pytest.fixture
def checker():
    return AccountRiskChecker()


@pytest.fixture
def normal_context():
    return RiskContext(
        equity=100000,
        initial_equity=100000,
        drawdown=0.05,
        daily_pnl=500,
    )


class TestAccountRiskChecker:
    """账户风控检查器测试"""
    
    @pytest.mark.asyncio
    async def test_normal_approve(self, checker, normal_context):
        """正常情况批准"""
        result = await checker.check(normal_context)
        assert result.approved is True
        assert result.level == RiskLevel.NORMAL
    
    @pytest.mark.asyncio
    async def test_drawdown_exceeded(self, checker):
        """回撤超限拒绝"""
        context = RiskContext(
            equity=75000,
            initial_equity=100000,
            drawdown=0.25,
            daily_pnl=-1000,
        )
        result = await checker.check(context)
        assert result.approved is False
        assert result.level == RiskLevel.RISK_LOCKED
        assert "回撤" in result.reason
    
    @pytest.mark.asyncio
    async def test_daily_loss_exceeded(self, checker):
        """单日亏损超限"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=-4000,  # 4% 亏损
        )
        result = await checker.check(context)
        assert result.approved is False
        assert result.level == RiskLevel.COOLDOWN
    
    @pytest.mark.asyncio
    async def test_consecutive_losses(self, checker):
        """连续亏损"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=0,
            consecutive_losses=3,
        )
        result = await checker.check(context)
        assert result.approved is False
        assert result.level == RiskLevel.COOLDOWN
    
    @pytest.mark.asyncio
    async def test_warning_level(self, checker):
        """接近阈值预警"""
        context = RiskContext(
            equity=83000,
            initial_equity=100000,
            drawdown=0.17,  # 85% of 20%, 超过 80% 阈值
            daily_pnl=0,
        )
        result = await checker.check(context)
        assert result.approved is True
        assert result.level == RiskLevel.WARNING
