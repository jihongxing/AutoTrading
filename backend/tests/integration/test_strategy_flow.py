"""
策略层集成测试

测试完整的策略流程：证人注册 → 信号生成 → Claim 聚合 → 冲突消解
"""

import pytest
from datetime import datetime, timedelta
from src.common.utils import utc_now

from src.common.enums import ClaimType, WitnessTier
from src.common.models import MarketBar
from src.strategy import (
    HealthManager,
    StrategyOrchestrator,
    WitnessRegistry,
    VolatilityReleaseWitness,
    RangeBreakWitness,
    TimeStructureWitness,
    RiskSentinelWitness,
    MacroSentinelWitness,
)
from src.strategy.health import TradeResult
from src.strategy.orchestrator import ConflictResolution


def create_market_data(count: int = 50) -> list[MarketBar]:
    """创建测试用市场数据"""
    bars = []
    price = 50000.0
    now_ms = int(utc_now().timestamp() * 1000)
    for i in range(count):
        change = price * 0.005 * (1 if i % 2 == 0 else -1)
        bars.append(MarketBar(
            ts=now_ms - (count - i) * 3600000,
            interval="1h",
            open=price,
            high=price + abs(change),
            low=price - abs(change),
            close=price + change,
            volume=1000.0 + i * 10,
        ))
        price = price + change
    return bars


class TestStrategyFlow:
    """策略流程集成测试"""
    
    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        registry = WitnessRegistry()
        health_manager = HealthManager()
        orchestrator = StrategyOrchestrator(registry, health_manager)
        return registry, health_manager, orchestrator
    
    @pytest.mark.asyncio
    async def test_full_witness_registration(self, setup):
        """测试完整证人注册"""
        registry, health_manager, _ = setup
        
        # 注册所有类型证人
        witnesses = [
            VolatilityReleaseWitness(),
            RangeBreakWitness(),
            TimeStructureWitness(),
            RiskSentinelWitness(),
            MacroSentinelWitness(),
        ]
        
        for w in witnesses:
            registry.register(w)
            health_manager.initialize_health(w)
        
        assert registry.count == 5
        assert len(registry.get_core_witnesses()) == 2
        assert len(registry.get_auxiliary_witnesses()) == 1
        assert len(registry.get_veto_witnesses()) == 2
    
    @pytest.mark.asyncio
    async def test_witness_run_and_aggregate(self, setup):
        """测试证人运行和聚合"""
        registry, health_manager, orchestrator = setup
        
        # 注册证人
        witnesses = [
            VolatilityReleaseWitness(),
            RangeBreakWitness(),
            TimeStructureWitness(),
        ]
        
        for w in witnesses:
            registry.register(w)
            health_manager.initialize_health(w)
        
        # 运行证人
        market_data = create_market_data(50)
        claims = await orchestrator.run_witnesses(market_data)
        
        # 聚合结果
        result = await orchestrator.aggregate_claims(claims)
        
        # 验证结果结构
        assert result.claims == claims
        assert result.resolution in ConflictResolution
    
    @pytest.mark.asyncio
    async def test_tier3_veto_flow(self, setup):
        """测试 TIER 3 否决流程"""
        registry, health_manager, orchestrator = setup
        
        # 注册证人
        vol_witness = VolatilityReleaseWitness()
        risk_witness = RiskSentinelWitness(max_consecutive_losses=2)
        
        registry.register(vol_witness)
        registry.register(risk_witness)
        health_manager.initialize_health(vol_witness)
        health_manager.initialize_health(risk_witness)
        
        # 模拟连续亏损
        risk_witness.record_trade_result(is_win=False)
        risk_witness.record_trade_result(is_win=False)
        
        # 运行证人
        market_data = create_market_data(50)
        claims = await orchestrator.run_witnesses(market_data)
        
        # 聚合结果
        result = await orchestrator.aggregate_claims(claims)
        
        # 验证否决
        assert result.resolution == ConflictResolution.VETOED
        assert not result.is_tradeable
    
    @pytest.mark.asyncio
    async def test_health_tracking_flow(self, setup):
        """测试健康度跟踪流程"""
        registry, health_manager, _ = setup
        
        witness = VolatilityReleaseWitness()
        registry.register(witness)
        health_manager.initialize_health(witness)
        
        # 模拟交易结果
        for i in range(60):
            result = TradeResult(
                strategy_id=witness.strategy_id,
                is_win=i < 35,  # 58% 胜率
                pnl=100.0 if i < 35 else -100.0,
                timestamp=utc_now(),
            )
            health_manager.update_health(witness.strategy_id, result)
        
        # 验证健康度
        health = health_manager.get_health(witness.strategy_id)
        assert health is not None
        assert health.sample_count == 60
        assert health.win_rate > 0.55
    
    @pytest.mark.asyncio
    async def test_muted_witness_excluded(self, setup):
        """测试静默证人被排除"""
        registry, health_manager, orchestrator = setup
        
        w1 = VolatilityReleaseWitness()
        w2 = RangeBreakWitness()
        
        registry.register(w1)
        registry.register(w2)
        
        # 静默 w1
        w1.mute()
        
        assert registry.active_count == 1
        
        # 运行证人
        market_data = create_market_data(50)
        claims = await orchestrator.run_witnesses(market_data)
        
        # 验证只有 w2 的 Claim
        for claim in claims:
            assert claim.strategy_id != w1.strategy_id
    
    @pytest.mark.asyncio
    async def test_high_trading_window_detection(self, setup):
        """测试高交易窗口检测"""
        registry, health_manager, orchestrator = setup
        
        # 注册证人
        witnesses = [
            VolatilityReleaseWitness(),
            RangeBreakWitness(),
            TimeStructureWitness(),
        ]
        
        for w in witnesses:
            registry.register(w)
        
        # 运行证人
        market_data = create_market_data(50)
        claims = await orchestrator.run_witnesses(market_data)
        
        # 检测高交易窗口
        window = await orchestrator.check_high_trading_window(claims)
        
        # 验证结果结构
        assert hasattr(window, "is_active")
        assert hasattr(window, "confidence")
        assert hasattr(window, "direction")

