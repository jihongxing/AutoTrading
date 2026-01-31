"""
BTC 自动交易系统 — 权重管理器
"""

from pathlib import Path

import yaml

from src.common.enums import HealthGrade
from src.common.logging import get_logger
from src.common.utils import utc_now

from ..health import HealthManager
from .models import HEALTH_FACTOR_MAP, WitnessWeight

logger = get_logger(__name__)


class WeightManager:
    """
    权重管理器
    
    管理证人权重：
    - base_weight: 从配置文件加载 (L1)
    - health_factor: 从 HealthManager 获取
    - learning_factor: 由 LearningEngine 设置
    """
    
    # 权重边界
    BASE_WEIGHT_MIN = 0.5
    BASE_WEIGHT_MAX = 2.0
    LEARNING_FACTOR_MIN = 0.8
    LEARNING_FACTOR_MAX = 1.2
    
    def __init__(
        self,
        health_manager: HealthManager | None = None,
        config_path: str | None = None,
    ):
        self.health_manager = health_manager
        self._weights: dict[str, WitnessWeight] = {}
        self._config: dict = {}
        
        if config_path:
            self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> None:
        """从配置文件加载基础权重"""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {config_path}")
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            
            weights_config = self._config.get("weights", {})
            for strategy_id, config in weights_config.items():
                base = config.get("base_weight", 1.0)
                self._weights[strategy_id] = WitnessWeight(
                    strategy_id=strategy_id,
                    base_weight=self._clamp_base(base),
                )
            
            logger.info(f"加载权重配置: {len(self._weights)} 个证人")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
    
    def get_weight(self, strategy_id: str) -> WitnessWeight:
        """
        获取权重（自动更新 health_factor）
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            权重对象
        """
        if strategy_id not in self._weights:
            self._weights[strategy_id] = WitnessWeight(strategy_id=strategy_id)
        
        weight = self._weights[strategy_id]
        
        # 更新 health_factor
        if self.health_manager:
            health = self.health_manager.get_health(strategy_id)
            if health:
                weight.health_factor = HEALTH_FACTOR_MAP.get(health.grade, 1.0)
                weight.updated_at = utc_now()
        
        return weight
    
    def get_all_weights(self) -> list[WitnessWeight]:
        """获取所有权重"""
        return list(self._weights.values())
    
    def set_base_weight(self, strategy_id: str, base: float) -> None:
        """
        设置基础权重（L1 配置）
        
        Args:
            strategy_id: 策略 ID
            base: 基础权重 (0.5-2.0)
        """
        if strategy_id not in self._weights:
            self._weights[strategy_id] = WitnessWeight(strategy_id=strategy_id)
        
        self._weights[strategy_id].base_weight = self._clamp_base(base)
        self._weights[strategy_id].updated_at = utc_now()
        
        logger.info(
            f"设置基础权重: {strategy_id} = {self._weights[strategy_id].base_weight}",
            extra={"strategy_id": strategy_id, "base_weight": base},
        )
    
    def set_learning_factor(self, strategy_id: str, factor: float) -> None:
        """
        设置学习因子（由 LearningEngine 调用）
        
        Args:
            strategy_id: 策略 ID
            factor: 学习因子 (0.8-1.2)
        """
        if strategy_id not in self._weights:
            self._weights[strategy_id] = WitnessWeight(strategy_id=strategy_id)
        
        self._weights[strategy_id].learning_factor = self._clamp_learning(factor)
        self._weights[strategy_id].updated_at = utc_now()
        
        logger.info(
            f"设置学习因子: {strategy_id} = {self._weights[strategy_id].learning_factor}",
            extra={"strategy_id": strategy_id, "learning_factor": factor},
        )
    
    def get_aggregation_config(self) -> dict:
        """获取聚合配置"""
        return self._config.get("aggregation", {
            "tier2_base_factor": 0.1,
            "confidence_threshold": 0.6,
        })
    
    def _clamp_base(self, value: float) -> float:
        """限制基础权重范围"""
        return max(self.BASE_WEIGHT_MIN, min(self.BASE_WEIGHT_MAX, value))
    
    def _clamp_learning(self, value: float) -> float:
        """限制学习因子范围"""
        return max(self.LEARNING_FACTOR_MIN, min(self.LEARNING_FACTOR_MAX, value))
