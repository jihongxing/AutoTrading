"""
BTC 自动交易系统 — 自学习常量

定义自学习模块的边界约束和调整频率。
"""

from src.common.constants import LearningBounds


# 复用 common 中的边界约束
WITNESS_WEIGHT_MIN = LearningBounds.WITNESS_WEIGHT_MIN
WITNESS_WEIGHT_MAX = LearningBounds.WITNESS_WEIGHT_MAX
POSITION_MULTIPLIER_MIN = LearningBounds.POSITION_MULTIPLIER_MIN
POSITION_MULTIPLIER_MAX = LearningBounds.POSITION_MULTIPLIER_MAX
DEFAULT_POSITION_MIN = LearningBounds.DEFAULT_POSITION_RATIO_MIN
DEFAULT_POSITION_MAX = LearningBounds.DEFAULT_POSITION_RATIO_MAX
STOP_ADJUSTMENT_MIN = LearningBounds.STOP_LOSS_ADJUSTMENT_MIN
STOP_ADJUSTMENT_MAX = LearningBounds.STOP_LOSS_ADJUSTMENT_MAX
MAX_DAILY_WEIGHT_CHANGE = LearningBounds.MAX_DAILY_WEIGHT_CHANGE


# 样本量要求
class SampleRequirements:
    """样本量要求"""
    MIN_TRADES_DAILY = 10
    MIN_TRADES_WEEKLY = 50
    MIN_TRADES_FOR_WEIGHT = 30
    MIN_TRADES_FOR_POSITION = 50
    MIN_TRADES_FOR_STOP = 100


# 调整频率
class AdjustmentFrequency:
    """调整频率"""
    WITNESS_WEIGHT = "daily"
    POSITION_MULTIPLIER = "daily"
    DEFAULT_POSITION = "weekly"
    STOP_LOSS = "weekly"
    TAKE_PROFIT = "weekly"
    WINDOW_THRESHOLD = "weekly"


# 权重调整阈值
class WeightAdjustmentThresholds:
    """权重调整阈值"""
    INCREASE_THRESHOLD = 0.55  # 成功率 > 55% 增加权重
    MAINTAIN_MIN = 0.52  # 成功率 52-55% 保持
    DECREASE_THRESHOLD = 0.50  # 成功率 < 50% 减少权重
    MUTE_THRESHOLD = 0.48  # 成功率 < 48% 静默
    
    INCREASE_AMOUNT = 0.05
    DECREASE_AMOUNT = 0.05


# 禁止触碰的参数
FORBIDDEN_PARAMS = frozenset([
    "max_drawdown",
    "daily_max_loss",
    "weekly_max_loss",
    "max_leverage",
    "max_single_position",
    "max_total_position",
])


# 有效学习状态
VALID_LEARNING_STATES = frozenset([
    "NORMAL",
    "WARNING",
])


# 排除的学习状态
EXCLUDED_LEARNING_STATES = frozenset([
    "COOLDOWN",
    "RISK_LOCKED",
    "HALTED",
])
