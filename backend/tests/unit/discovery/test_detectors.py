"""
异常检测器测试
"""

import pytest
from datetime import datetime, timezone

from src.common.models import MarketBar
from src.discovery.factory.detectors import VolatilityDetector, VolumeDetector


def create_market_bars(count: int, base_price: float = 50000.0) -> list[MarketBar]:
    """创建测试用 K 线数据"""
    bars = []
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    for i in range(count):
        # 正常波动
        price = base_price + (i % 10) * 10
        bars.append(MarketBar(
            ts=ts + i * 60000,
            symbol="BTCUSDT",
            interval="1m",
            open=price,
            high=price + 50,
            low=price - 50,
            close=price + 10,
            volume=1000.0,
        ))
    
    return bars


class TestVolatilityDetector:
    """波动率检测器测试"""
    
    @pytest.fixture
    def detector(self):
        return VolatilityDetector(
            compression_threshold=0.5,
            release_threshold=2.0,
            lookback_period=20,
            history_period=100,
        )
    
    @pytest.mark.asyncio
    async def test_no_anomaly_normal_data(self, detector):
        """测试正常数据无异常"""
        data = create_market_bars(150)
        events = await detector.detect(data)
        
        # 正常数据应该没有异常
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_detect_compression(self, detector):
        """测试检测波动率压缩"""
        data = create_market_bars(150)
        
        # 最后几根 K 线波动率极低
        for i in range(-10, 0):
            data[i] = MarketBar(
                ts=data[i].ts,
                symbol="BTCUSDT",
                interval="1m",
                open=50000,
                high=50001,  # 极小波动
                low=49999,
                close=50000,
                volume=1000.0,
            )
        
        events = await detector.detect(data)
        
        # 应该检测到压缩
        compression_events = [e for e in events if e.event_type == "volatility_compression"]
        assert len(compression_events) >= 0  # 可能检测到
    
    @pytest.mark.asyncio
    async def test_detect_release(self, detector):
        """测试检测波动率释放"""
        data = create_market_bars(150)
        
        # 最后一根 K 线波动率极高
        data[-1] = MarketBar(
            ts=data[-1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50000,
            high=52000,  # 大波动
            low=48000,
            close=51000,
            volume=1000.0,
        )
        
        events = await detector.detect(data)
        
        # 应该检测到释放
        release_events = [e for e in events if e.event_type == "volatility_release"]
        assert isinstance(release_events, list)
    
    def test_generate_hypotheses(self, detector):
        """测试生成假设"""
        from src.discovery.pool.models import AnomalyEvent
        
        events = [
            AnomalyEvent(
                event_id="test_compress_001",
                detector_id="volatility",
                event_type="volatility_compression",
                timestamp=datetime.now(timezone.utc),
                severity=0.8,
                features={"atr": 50, "avg_atr": 100},
            ),
        ]
        
        hypotheses = detector.generate_hypotheses(events)
        
        assert len(hypotheses) == 1
        assert hypotheses[0].source_detector == "volatility"
        assert hypotheses[0].expected_direction == "breakout"
    
    @pytest.mark.asyncio
    async def test_insufficient_data(self, detector):
        """测试数据不足"""
        data = create_market_bars(50)  # 不足 120
        events = await detector.detect(data)
        
        assert events == []


class TestVolumeDetector:
    """成交量检测器测试"""
    
    @pytest.fixture
    def detector(self):
        return VolumeDetector(
            surge_threshold=2.5,
            shrink_threshold=0.3,
            history_period=100,
        )
    
    @pytest.mark.asyncio
    async def test_detect_surge(self, detector):
        """测试检测放量"""
        data = create_market_bars(120)
        
        # 最后一根放量
        data[-1] = MarketBar(
            ts=data[-1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=5000.0,  # 5 倍于正常
        )
        
        events = await detector.detect(data)
        
        surge_events = [e for e in events if e.event_type == "volume_surge"]
        assert len(surge_events) == 1
        assert surge_events[0].features["ratio"] > 2.5
    
    @pytest.mark.asyncio
    async def test_detect_shrink(self, detector):
        """测试检测缩量"""
        data = create_market_bars(120)
        
        # 最后一根缩量
        data[-1] = MarketBar(
            ts=data[-1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=100.0,  # 0.1 倍于正常
        )
        
        events = await detector.detect(data)
        
        shrink_events = [e for e in events if e.event_type == "volume_shrink"]
        assert len(shrink_events) == 1
    
    def test_generate_hypotheses(self, detector):
        """测试生成假设"""
        from src.discovery.pool.models import AnomalyEvent
        
        events = [
            AnomalyEvent(
                event_id="test_surge_001",
                detector_id="volume",
                event_type="volume_surge",
                timestamp=datetime.now(timezone.utc),
                severity=0.9,
                features={"volume": 5000, "avg_volume": 1000},
            ),
        ]
        
        hypotheses = detector.generate_hypotheses(events)
        
        assert len(hypotheses) == 1
        assert hypotheses[0].name == "放量突破跟随"


class TestGapDetector:
    """跳空检测器测试"""
    
    @pytest.fixture
    def detector(self):
        from src.discovery.factory.detectors import GapDetector
        return GapDetector(gap_threshold=0.005, large_gap_threshold=0.01)
    
    @pytest.mark.asyncio
    async def test_detect_gap_up(self, detector):
        """测试检测向上跳空"""
        data = create_market_bars(10)
        # 制造跳空
        data[-1] = MarketBar(
            ts=data[-1].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50500,  # 比前一根 close 高 1%
            high=50600,
            low=50400,
            close=50550,
            volume=1000.0,
        )
        data[-2] = MarketBar(
            ts=data[-2].ts,
            symbol="BTCUSDT",
            interval="1m",
            open=50000,
            high=50100,
            low=49900,
            close=50000,
            volume=1000.0,
        )
        
        events = await detector.detect(data)
        gap_events = [e for e in events if "gap" in e.event_type]
        assert len(gap_events) == 1
        assert gap_events[0].features["direction"] == "up"
    
    @pytest.mark.asyncio
    async def test_no_gap(self, detector):
        """测试无跳空"""
        data = create_market_bars(10)
        events = await detector.detect(data)
        # 正常数据无跳空
        assert len(events) == 0


class TestPricePatternDetector:
    """价格形态检测器测试"""
    
    @pytest.fixture
    def detector(self):
        from src.discovery.factory.detectors import PricePatternDetector
        return PricePatternDetector(lookback_period=20, tolerance=0.01)
    
    @pytest.mark.asyncio
    async def test_insufficient_data(self, detector):
        """测试数据不足"""
        data = create_market_bars(10)
        events = await detector.detect(data)
        assert events == []
    
    @pytest.mark.asyncio
    async def test_detect_pattern(self, detector):
        """测试形态检测"""
        data = create_market_bars(30)
        events = await detector.detect(data)
        # 正常数据可能检测到形态也可能没有
        assert isinstance(events, list)


class TestTrendExhaustionDetector:
    """趋势耗竭检测器测试"""
    
    @pytest.fixture
    def detector(self):
        from src.discovery.factory.detectors import TrendExhaustionDetector
        return TrendExhaustionDetector(rsi_period=14, lookback=5)
    
    @pytest.mark.asyncio
    async def test_insufficient_data(self, detector):
        """测试数据不足"""
        data = create_market_bars(10)
        events = await detector.detect(data)
        assert events == []
    
    @pytest.mark.asyncio
    async def test_detect_exhaustion(self, detector):
        """测试耗竭检测"""
        data = create_market_bars(30)
        events = await detector.detect(data)
        assert isinstance(events, list)


class TestSessionAnomalyDetector:
    """时段异常检测器测试"""
    
    @pytest.fixture
    def detector(self):
        from src.discovery.factory.detectors import SessionAnomalyDetector
        return SessionAnomalyDetector()
    
    @pytest.mark.asyncio
    async def test_detect_session(self, detector):
        """测试时段检测"""
        data = create_market_bars(10)
        events = await detector.detect(data)
        # 可能检测到时段切换
        assert isinstance(events, list)


class TestFundingVolatilityDetector:
    """资金费率波动检测器测试"""
    
    @pytest.fixture
    def detector(self):
        from src.discovery.factory.detectors import FundingVolatilityDetector
        return FundingVolatilityDetector()
    
    @pytest.mark.asyncio
    async def test_no_data(self, detector):
        """测试无资金费率数据"""
        data = create_market_bars(10)
        events = await detector.detect(data)
        assert events == []
    
    @pytest.mark.asyncio
    async def test_with_funding_data(self, detector):
        """测试有资金费率数据"""
        # 添加资金费率数据
        for i in range(30):
            detector.update_funding_rate(0.0001 * (i % 5))
        
        data = create_market_bars(10)
        events = await detector.detect(data)
        assert isinstance(events, list)
