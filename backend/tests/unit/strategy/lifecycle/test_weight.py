"""
权重管理器测试
"""

import pytest
from unittest.mock import MagicMock

from src.common.enums import HealthGrade, WitnessStatus, WitnessTier
from src.common.models import WitnessHealth
from src.strategy.lifecycle.models import HEALTH_FACTOR_MAP, WitnessWeight
from src.strategy.lifecycle.weight import WeightManager


class TestWitnessWeight:
    """WitnessWeight 模型测试"""
    
    def test_effective_weight_default(self):
        """默认有效权重"""
        weight = WitnessWeight(strategy_id="test")
        assert weight.effective_weight == 1.0
    
    def test_effective_weight_calculation(self):
        """有效权重计算"""
        weight = WitnessWeight(
            strategy_id="test",
            base_weight=1.5,
            health_factor=1.2,
            learning_factor=1.1,
        )
        expected = 1.5 * 1.2 * 1.1
        assert abs(weight.effective_weight - expected) < 0.001
    
    def test_to_dict(self):
        """序列化"""
        weight = WitnessWeight(strategy_id="test", base_weight=1.5)
        data = weight.to_dict()
        assert data["strategy_id"] == "test"
        assert data["base_weight"] == 1.5
        assert "effective_weight" in data


class TestHealthFactorMap:
    """健康度因子映射测试"""
    
    def test_grade_a(self):
        assert HEALTH_FACTOR_MAP[HealthGrade.A] == 1.2
    
    def test_grade_b(self):
        assert HEALTH_FACTOR_MAP[HealthGrade.B] == 1.0
    
    def test_grade_c(self):
        assert HEALTH_FACTOR_MAP[HealthGrade.C] == 0.7
    
    def test_grade_d(self):
        assert HEALTH_FACTOR_MAP[HealthGrade.D] == 0.5


class TestWeightManager:
    """WeightManager 测试"""
    
    def test_init_without_config(self):
        """无配置初始化"""
        manager = WeightManager()
        assert manager._weights == {}
    
    def test_get_weight_creates_default(self):
        """获取不存在的权重创建默认值"""
        manager = WeightManager()
        weight = manager.get_weight("new_strategy")
        assert weight.strategy_id == "new_strategy"
        assert weight.base_weight == 1.0
    
    def test_set_base_weight(self):
        """设置基础权重"""
        manager = WeightManager()
        manager.set_base_weight("test", 1.5)
        weight = manager.get_weight("test")
        assert weight.base_weight == 1.5
    
    def test_set_base_weight_clamp_min(self):
        """基础权重下限"""
        manager = WeightManager()
        manager.set_base_weight("test", 0.1)
        weight = manager.get_weight("test")
        assert weight.base_weight == 0.5
    
    def test_set_base_weight_clamp_max(self):
        """基础权重上限"""
        manager = WeightManager()
        manager.set_base_weight("test", 5.0)
        weight = manager.get_weight("test")
        assert weight.base_weight == 2.0
    
    def test_set_learning_factor(self):
        """设置学习因子"""
        manager = WeightManager()
        manager.set_learning_factor("test", 1.1)
        weight = manager.get_weight("test")
        assert weight.learning_factor == 1.1
    
    def test_set_learning_factor_clamp_min(self):
        """学习因子下限"""
        manager = WeightManager()
        manager.set_learning_factor("test", 0.5)
        weight = manager.get_weight("test")
        assert weight.learning_factor == 0.8
    
    def test_set_learning_factor_clamp_max(self):
        """学习因子上限"""
        manager = WeightManager()
        manager.set_learning_factor("test", 1.5)
        weight = manager.get_weight("test")
        assert weight.learning_factor == 1.2
    
    def test_health_factor_update(self):
        """健康度因子更新"""
        health_manager = MagicMock()
        health_manager.get_health.return_value = WitnessHealth(
            witness_id="test",
            tier=WitnessTier.TIER_2,
            status=WitnessStatus.ACTIVE,
            grade=HealthGrade.A,
            win_rate=0.6,
            sample_count=100,
            weight=0.5,
        )
        
        manager = WeightManager(health_manager=health_manager)
        weight = manager.get_weight("test")
        
        assert weight.health_factor == 1.2
    
    def test_get_all_weights(self):
        """获取所有权重"""
        manager = WeightManager()
        manager.set_base_weight("a", 1.0)
        manager.set_base_weight("b", 1.5)
        
        weights = manager.get_all_weights()
        assert len(weights) == 2
    
    def test_aggregation_config_default(self):
        """默认聚合配置"""
        manager = WeightManager()
        config = manager.get_aggregation_config()
        assert config["tier2_base_factor"] == 0.1
        assert config["confidence_threshold"] == 0.6
