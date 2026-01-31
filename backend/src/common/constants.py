"""
BTC 自动交易系统 — 宪法级常量

L0 层级：永不修改，硬编码在系统中。
"""


class ArchitectureConstants:
    """
    宪法级常量 — 永不修改
    
    违反这些常量的代码将触发 ArchitectureViolationError。
    """
    
    # ========================================
    # 三权分立
    # ========================================
    
    # 策略无下单权
    STRATEGY_CAN_PLACE_ORDER: bool = False
    
    # 风控硬否决权
    RISK_CONTROL_HAS_VETO: bool = True
    
    # 状态机是唯一交易入口
    STATE_MACHINE_IS_ONLY_ENTRY: bool = True
    
    # ========================================
    # 证人体系
    # ========================================
    
    # TIER3 一票否决
    TIER3_HAS_ABSOLUTE_VETO: bool = True
    
    # 最少 2 个证人同意才能交易
    MIN_WITNESSES_FOR_TRADE: int = 2
    
    # 核心:辅助权重比
    CORE_AUXILIARY_WEIGHT_RATIO: float = 2.0
    
    # ========================================
    # 风控优先级
    # ========================================
    
    # 风控优先于策略
    RISK_PRIORITY_OVER_STRATEGY: bool = True


class LearningBounds:
    """
    自学习边界约束
    
    L3 参数只能在这些范围内调整。
    """
    
    # 证人权重范围
    WITNESS_WEIGHT_MIN: float = 0.1
    WITNESS_WEIGHT_MAX: float = 0.9
    
    # 仓位放大系数范围
    POSITION_MULTIPLIER_MIN: float = 0.5
    POSITION_MULTIPLIER_MAX: float = 1.5
    
    # 默认仓位比例范围
    DEFAULT_POSITION_RATIO_MIN: float = 0.01  # 1%
    DEFAULT_POSITION_RATIO_MAX: float = 0.03  # 3%
    
    # 止损微调范围
    STOP_LOSS_ADJUSTMENT_MIN: float = -0.005  # -0.5%
    STOP_LOSS_ADJUSTMENT_MAX: float = 0.005   # +0.5%
    
    # 止盈微调范围
    TAKE_PROFIT_ADJUSTMENT_MIN: float = -0.005
    TAKE_PROFIT_ADJUSTMENT_MAX: float = 0.005
    
    # 单日最大权重调整幅度
    MAX_DAILY_WEIGHT_CHANGE: float = 0.05  # 5%


# 自学习禁止触碰的参数（L2 风控阈值）
LEARNING_FORBIDDEN_PARAMS: list[str] = [
    "max_drawdown",
    "daily_max_loss",
    "weekly_max_loss",
    "max_leverage",
    "max_single_position",
    "max_total_position",
    "consecutive_loss_cooldown",
]
