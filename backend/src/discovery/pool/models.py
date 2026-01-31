"""
BTC 自动交易系统 — 假设工厂数据模型

定义异常事件、假设、验证结果等核心模型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.enums import HypothesisStatus
from src.common.utils import utc_now


@dataclass
class AnomalyEvent:
    """
    异常事件
    
    由检测器检测到的市场异常。
    """
    event_id: str
    detector_id: str
    event_type: str  # volatility_compression / volume_surge / funding_extreme / ...
    timestamp: datetime
    severity: float  # 0-1，异常强度
    features: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """
    验证结果
    
    假设的统计验证结果。
    """
    p_value: float
    win_rate: float
    cohens_d: float
    sample_size: int
    is_robust: bool  # ±20% 参数不翻转
    correlation_max: float  # 与现有证人的最大相关性
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0


@dataclass
class Hypothesis:
    """
    策略假设
    
    由检测器从异常事件生成的策略假设。
    """
    id: str
    name: str
    status: HypothesisStatus
    
    # 来源
    source_detector: str
    source_event: str
    
    # 事件定义（机械化、可执行）
    event_definition: str  # Python 表达式
    event_params: dict[str, float]
    
    # 预期效应
    expected_direction: str  # long / short / breakout
    expected_win_rate: tuple[float, float]  # (min, max)
    
    # 验证结果
    validation_result: ValidationResult | None = None
    
    # 相关性
    correlation_with_existing: dict[str, float] = field(default_factory=dict)
    
    # 元数据
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    def update_status(self, new_status: HypothesisStatus) -> None:
        """更新状态"""
        self.status = new_status
        self.updated_at = utc_now()
    
    def set_validation_result(self, result: ValidationResult) -> None:
        """设置验证结果"""
        self.validation_result = result
        self.updated_at = utc_now()
    
    @property
    def is_promotable(self) -> bool:
        """是否可晋升为证人"""
        return self.status in (HypothesisStatus.TIER_1, HypothesisStatus.TIER_2)
    
    @property
    def is_valid(self) -> bool:
        """是否有效（非失败/废弃）"""
        return self.status not in (HypothesisStatus.FAIL, HypothesisStatus.DEPRECATED)
