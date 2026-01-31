"""
假设工厂集成测试

测试完整的发现流程：检测 → 生成 → 验证 → 晋升
"""

import pytest
from datetime import datetime, timezone

from src.common.enums import HypothesisStatus
from src.common.models import MarketBar
from src.discovery.factory import HypothesisFactory, VolatilityDetector, VolumeDetector
from src.discovery.pool import HypothesisPoolManager
from src.discovery.promoter import WitnessGenerator
from src.discovery.validator import HypothesisValidator
from src.learning.collector import TradeData
from src.strategy.health import HealthManager
from src.strategy.registry import WitnessRegistry


def create_market_bars(count: int) -> list[MarketBar]:
    """创建测试用 K 线数据"""
    bars = []
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    for i in range(count):
        bars.append(MarketBar(
            ts=ts + i * 60000,
            symbol="BTCUSDT",
            interval="1m",
            open=50000 + i * 10,
            high=50100 + i * 10,
            low=49900 + i * 10,
            close=50050 + i * 10,
            volume=1000.0,
        ))
    
    return bars


def create_trade_data(count: int, win_rate: float) -> list[TradeData]:
    """创建测试用交易数据"""
    trades = []
    wins = int(count * win_rate)
    
    for i in range(count):
        is_win = i < wins
        trades.append(TradeData(
            trade_id=f"trade_{i}",
            timestamp=datetime.now(timezone.utc),
            symbol="BTCUSDT",
            direction="long",
            entry_price=50000.0,
            exit_price=50100.0 if is_win else 49900.0,
            quantity=0.1,
            pnl=10.0 if is_win else -10.0,
            is_win=is_win,
            witness_ids=["test_witness"],
            state_at_entry="active_trading",
        ))
    
    return trades


class TestDiscoveryFlow:
    """假设工厂集成测试"""
    
    @pytest.fixture
    def factory(self):
        """创建假设工厂"""
        f = HypothesisFactory()
        f.register_detector(VolatilityDetector())
        f.register_detector(VolumeDetector())
        return f
    
    @pytest.fixture
    def pool_manager(self):
        """创建候选池管理器"""
        return HypothesisPoolManager()
    
    @pytest.fixture
    def validator(self):
        """创建验证器"""
        return HypothesisValidator()
    
    @pytest.fixture
    def generator(self):
        """创建证人生成器"""
        registry = WitnessRegistry()
        health_manager = HealthManager()
        return WitnessGenerator(registry, health_manager)
    
    @pytest.mark.asyncio
    async def test_factory_registration(self, factory):
        """测试检测器注册"""
        assert factory.detector_count == 2
        assert "volatility" in factory.detector_ids
        assert "volume" in factory.detector_ids
    
    @pytest.mark.asyncio
    async def test_scan_for_anomalies(self, factory):
        """测试异常扫描"""
        data = create_market_bars(150)
        
        # 添加异常数据
        data[-1] = MarketBar(
            ts=data[-1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=5000.0,  # 放量
        )
        
        events = await factory.scan_for_anomalies(data)
        
        assert isinstance(events, list)
    
    @pytest.mark.asyncio
    async def test_generate_hypotheses(self, factory):
        """测试假设生成"""
        data = create_market_bars(150)
        
        # 添加放量
        data[-1] = MarketBar(
            ts=data[-1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=5000.0,
        )
        
        events = await factory.scan_for_anomalies(data)
        hypotheses = factory.generate_hypotheses(events)
        
        assert isinstance(hypotheses, list)

    @pytest.mark.asyncio
    async def test_pool_management(self, factory, pool_manager):
        """测试候选池管理"""
        data = create_market_bars(150)
        data[-1] = MarketBar(
            ts=data[-1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=5000.0,
        )
        
        events = await factory.scan_for_anomalies(data)
        hypotheses = factory.generate_hypotheses(events)
        
        # 添加到候选池
        for h in hypotheses:
            await pool_manager.add(h)
        
        assert pool_manager.count == len(hypotheses)
    
    @pytest.mark.asyncio
    async def test_validation_flow(self, validator):
        """测试验证流程"""
        from src.discovery.pool.models import Hypothesis
        
        hypothesis = Hypothesis(
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
        
        trades = create_trade_data(150, win_rate=0.55)
        
        result = await validator.validate(hypothesis, trades)
        tier = validator.determine_tier(result)
        
        assert result.sample_size == 150
        assert tier in [HypothesisStatus.TIER_1, HypothesisStatus.TIER_2, HypothesisStatus.TIER_3, HypothesisStatus.FAIL]
    
    @pytest.mark.asyncio
    async def test_promotion_flow(self, generator):
        """测试晋升流程"""
        from src.discovery.pool.models import Hypothesis
        
        hypothesis = Hypothesis(
            id="hyp_promote_001",
            name="可晋升假设",
            status=HypothesisStatus.TIER_1,
            source_detector="volatility",
            source_event="event_001",
            event_definition="test",
            event_params={"compression_threshold": 0.5, "lookback_period": 20.0},
            expected_direction="breakout",
            expected_win_rate=(0.52, 0.55),
        )
        
        witness = generator.generate_and_register(hypothesis)
        
        assert witness is not None
        assert hypothesis.status == HypothesisStatus.PROMOTED
    
    @pytest.mark.asyncio
    async def test_full_discovery_pipeline(self, factory, pool_manager, validator, generator):
        """测试完整发现流程"""
        # 1. 扫描异常
        data = create_market_bars(150)
        data[-1] = MarketBar(
            ts=data[-1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=5000.0,
        )
        
        events = await factory.scan_for_anomalies(data)
        
        # 2. 生成假设
        hypotheses = factory.generate_hypotheses(events)
        
        # 3. 添加到候选池
        for h in hypotheses:
            await pool_manager.add(h)
        
        # 4. 验证（模拟）
        trades = create_trade_data(150, win_rate=0.55)
        
        for h in await pool_manager.get_all():
            result = await validator.validate(h, trades)
            tier = validator.determine_tier(result)
            await pool_manager.update_status(h.id, tier)
        
        # 5. 晋升
        promotable = await pool_manager.get_promotable()
        for h in promotable:
            generator.generate_and_register(h)
        
        # 验证流程完成
        stats = pool_manager.get_statistics()
        assert "total" in stats
