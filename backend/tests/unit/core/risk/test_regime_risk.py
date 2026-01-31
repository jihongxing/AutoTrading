"""策略失效风控测试"""

import pytest

from src.common.enums import HealthGrade, RiskLevel, WitnessStatus, WitnessTier
from src.common.models import WitnessHealth
from src.core.risk.regime_risk import RegimeRiskChecker
from src.core.risk.base import RiskContext


@pytest.fixture
def checker():
    return RegimeRiskChecker()


@pytest.fixture
def healthy_witnesses():
    return {
        "w1": WitnessHealth(
            witness_id="w1",
            tier=WitnessTier.TIER_1,
            status=WitnessStatus.ACTIVE,
            grade=HealthGrade.B,
            win_rate=0.55,
            sample_count=100,
            weight=0.6,
        ),
        "w2": WitnessHealth(
            witness_id="w2",
            tier=WitnessTier.TIER_2,
            status=WitnessStatus.ACTIVE,
            grade=HealthGrade.B,
            win_rate=0.52,
            sample_count=80,
            weight=0.4,
        ),
    }


class TestRegimeRiskChecker:
    """策略失效风控检查器测试"""
    
    @pytest.mark.asyncio
    async def test_normal_approve(self, checker, healthy_witnesses):
        """正常情况批准"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=0,
            witness_health=healthy_witnesses,
        )
        result = await checker.check(context)
        assert result.approved is True
        assert result.level == RiskLevel.NORMAL
    
    @pytest.mark.asyncio
    async def test_no_witnesses(self, checker):
        """无证人数据"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=0,
        )
        result = await checker.check(context)
        assert result.approved is True
    
    @pytest.mark.asyncio
    async def test_insufficient_witnesses(self, checker):
        """活跃证人不足"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=0,
            witness_health={
                "w1": WitnessHealth(
                    witness_id="w1",
                    tier=WitnessTier.TIER_1,
                    status=WitnessStatus.MUTED,
                    grade=HealthGrade.D,
                    win_rate=0.45,
                    sample_count=100,
                ),
            },
        )
        result = await checker.check(context)
        assert result.approved is True
        assert result.level == RiskLevel.WARNING
    
    @pytest.mark.asyncio
    async def test_low_win_rate(self, checker):
        """胜率过低"""
        context = RiskContext(
            equity=100000,
            initial_equity=100000,
            drawdown=0.05,
            daily_pnl=0,
            witness_health={
                "w1": WitnessHealth(
                    witness_id="w1",
                    tier=WitnessTier.TIER_1,
                    status=WitnessStatus.ACTIVE,
                    grade=HealthGrade.D,
                    win_rate=0.25,
                    sample_count=100,
                    weight=0.5,
                ),
                "w2": WitnessHealth(
                    witness_id="w2",
                    tier=WitnessTier.TIER_2,
                    status=WitnessStatus.ACTIVE,
                    grade=HealthGrade.D,
                    win_rate=0.28,
                    sample_count=80,
                    weight=0.5,
                ),
            },
        )
        result = await checker.check(context)
        assert result.approved is True
        assert result.level == RiskLevel.WARNING
        assert len(result.events) > 0
