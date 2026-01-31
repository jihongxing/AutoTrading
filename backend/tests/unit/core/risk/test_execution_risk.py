"""执行风控测试"""

import pytest

from src.common.enums import RiskLevel
from src.core.risk.execution_risk import ExecutionRiskChecker
from src.core.risk.base import RiskContext


@pytest.fixture
def checker():
    return ExecutionRiskChecker()


@pytest.fixture
def normal_context():
    return RiskContext(
        equity=100000,
        initial_equity=100000,
        drawdown=0.05,
        daily_pnl=0,
    )


class TestExecutionRiskChecker:
    """执行风控检查器测试"""
    
    @pytest.mark.asyncio
    async def test_normal_approve(self, checker, normal_context):
        """正常情况批准"""
        result = await checker.check(normal_context)
        assert result.approved is True
        assert result.level == RiskLevel.NORMAL
    
    @pytest.mark.asyncio
    async def test_high_slippage_warning(self, checker):
        """滑点过高警告"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=0,
            recent_slippages=[0.006, 0.007, 0.008],  # 平均 0.7%
        )
        result = await checker.check(context)
        assert result.approved is True
        assert result.level == RiskLevel.WARNING
        assert len(result.events) > 0
    
    @pytest.mark.asyncio
    async def test_severe_slippage_reject(self, checker):
        """滑点严重拒绝"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=0,
            recent_slippages=[0.012, 0.015, 0.018],  # 平均 1.5%
        )
        result = await checker.check(context)
        assert result.approved is False
        assert result.level == RiskLevel.COOLDOWN
    
    @pytest.mark.asyncio
    async def test_low_fill_rate(self, checker):
        """成交率过低"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=0,
            recent_fill_rates=[0.90, 0.88, 0.92],  # 平均 90%
        )
        result = await checker.check(context)
        assert result.approved is True
        assert result.level == RiskLevel.WARNING
    
    @pytest.mark.asyncio
    async def test_high_latency(self, checker):
        """延迟过高"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=0,
            recent_latencies=[1200, 1500, 1100],  # 平均 1267ms
        )
        result = await checker.check(context)
        assert result.approved is True
        assert result.level == RiskLevel.WARNING
