"""
假设工厂数据模型测试
"""

import pytest
from datetime import datetime, timezone

from src.common.enums import HypothesisStatus
from src.discovery.pool.models import AnomalyEvent, Hypothesis, ValidationResult


class TestAnomalyEvent:
    """异常事件模型测试"""
    
    def test_create_anomaly_event(self):
        """测试创建异常事件"""
        event = AnomalyEvent(
            event_id="test_event_001",
            detector_id="volatility",
            event_type="volatility_compression",
            timestamp=datetime.now(timezone.utc),
            severity=0.8,
            features={"atr": 100.0, "avg_atr": 200.0},
        )
        
        assert event.event_id == "test_event_001"
        assert event.detector_id == "volatility"
        assert event.severity == 0.8
        assert event.features["atr"] == 100.0
    
    def test_anomaly_event_with_metadata(self):
        """测试带元数据的异常事件"""
        event = AnomalyEvent(
            event_id="test_event_002",
            detector_id="volume",
            event_type="volume_surge",
            timestamp=datetime.now(timezone.utc),
            severity=0.9,
            features={"volume": 1000.0},
            metadata={"symbol": "BTCUSDT"},
        )
        
        assert event.metadata["symbol"] == "BTCUSDT"


class TestValidationResult:
    """验证结果模型测试"""
    
    def test_create_validation_result(self):
        """测试创建验证结果"""
        result = ValidationResult(
            p_value=0.03,
            win_rate=0.54,
            cohens_d=0.35,
            sample_size=150,
            is_robust=True,
            correlation_max=0.3,
        )
        
        assert result.p_value == 0.03
        assert result.win_rate == 0.54
        assert result.is_robust is True


class TestHypothesis:
    """假设模型测试"""
    
    def test_create_hypothesis(self):
        """测试创建假设"""
        hypothesis = Hypothesis(
            id="hyp_test_001",
            name="测试假设",
            status=HypothesisStatus.NEW,
            source_detector="volatility",
            source_event="event_001",
            event_definition="atr < avg_atr * 0.5",
            event_params={"compression_threshold": 0.5},
            expected_direction="breakout",
            expected_win_rate=(0.52, 0.55),
        )
        
        assert hypothesis.id == "hyp_test_001"
        assert hypothesis.status == HypothesisStatus.NEW
        assert hypothesis.expected_direction == "breakout"
    
    def test_update_status(self):
        """测试更新状态"""
        hypothesis = Hypothesis(
            id="hyp_test_002",
            name="测试假设",
            status=HypothesisStatus.NEW,
            source_detector="volatility",
            source_event="event_002",
            event_definition="test",
            event_params={},
            expected_direction="long",
            expected_win_rate=(0.51, 0.54),
        )
        
        old_updated = hypothesis.updated_at
        hypothesis.update_status(HypothesisStatus.TIER_1)
        
        assert hypothesis.status == HypothesisStatus.TIER_1
        assert hypothesis.updated_at >= old_updated
    
    def test_is_promotable(self):
        """测试是否可晋升"""
        hypothesis = Hypothesis(
            id="hyp_test_003",
            name="测试假设",
            status=HypothesisStatus.TIER_1,
            source_detector="volatility",
            source_event="event_003",
            event_definition="test",
            event_params={},
            expected_direction="long",
            expected_win_rate=(0.52, 0.55),
        )
        
        assert hypothesis.is_promotable is True
        
        hypothesis.update_status(HypothesisStatus.FAIL)
        assert hypothesis.is_promotable is False
    
    def test_is_valid(self):
        """测试是否有效"""
        hypothesis = Hypothesis(
            id="hyp_test_004",
            name="测试假设",
            status=HypothesisStatus.TIER_2,
            source_detector="volatility",
            source_event="event_004",
            event_definition="test",
            event_params={},
            expected_direction="short",
            expected_win_rate=(0.51, 0.53),
        )
        
        assert hypothesis.is_valid is True
        
        hypothesis.update_status(HypothesisStatus.DEPRECATED)
        assert hypothesis.is_valid is False
