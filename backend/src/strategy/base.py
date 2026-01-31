"""
BTC 自动交易系统 — 策略基类

所有策略必须继承此基类。
基类通过架构约束确保策略只能输出 Claim，不能直接下单。
"""

from abc import ABC, abstractmethod
from typing import Any

from src.common.constants import ArchitectureConstants
from src.common.enums import ClaimType, WitnessStatus, WitnessTier
from src.common.exceptions import ArchitectureViolationError, WitnessMutedError
from src.common.models import Claim, MarketBar, WitnessHealth


class BaseStrategy(ABC):
    """
    策略基类（证人）
    
    架构约束：
    - 只能输出 Claim，不能直接下单
    - 不能感知账户余额
    - 不能计算最终仓位
    
    子类必须实现：
    - generate_claim(): 生成策略声明
    """
    
    def __init__(
        self,
        strategy_id: str,
        tier: WitnessTier,
        validity_window: int = 60,
    ):
        self.strategy_id = strategy_id
        self.tier = tier
        self.validity_window = validity_window
        self._status = WitnessStatus.ACTIVE
        self._health: WitnessHealth | None = None
    
    # ========================================
    # 唯一合法输出方法
    # ========================================
    
    @abstractmethod
    def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
        """
        生成策略声明（唯一合法输出）
        
        Args:
            market_data: K 线数据
            
        Returns:
            Claim 或 None（无信号时）
        """
        pass
    
    def run(self, market_data: list[MarketBar]) -> Claim | None:
        """
        运行策略
        
        检查状态后调用 generate_claim()。
        """
        if self._status == WitnessStatus.MUTED:
            raise WitnessMutedError(f"证人 {self.strategy_id} 已被静默")
        
        if self._status == WitnessStatus.BANNED:
            raise WitnessMutedError(f"证人 {self.strategy_id} 已被封禁")
        
        return self.generate_claim(market_data)
    
    # ========================================
    # 禁止的方法（架构约束）
    # ========================================
    
    def place_order(self, *args: Any, **kwargs: Any) -> None:
        """禁止：策略无下单权"""
        raise ArchitectureViolationError(
            f"策略 {self.strategy_id} 试图直接下单，违反宪法级原则：策略无下单权",
            details={"strategy_id": self.strategy_id, "args": args, "kwargs": kwargs}
        )
    
    def execute_trade(self, *args: Any, **kwargs: Any) -> None:
        """禁止：策略无下单权"""
        raise ArchitectureViolationError(
            f"策略 {self.strategy_id} 试图执行交易，违反宪法级原则：策略无下单权"
        )
    
    def get_account_balance(self) -> None:
        """禁止：策略不能感知账户余额"""
        raise ArchitectureViolationError(
            f"策略 {self.strategy_id} 试图获取账户余额，违反架构约束"
        )
    
    def calculate_position_size(self, *args: Any, **kwargs: Any) -> None:
        """禁止：策略不能计算最终仓位"""
        raise ArchitectureViolationError(
            f"策略 {self.strategy_id} 试图计算仓位，违反架构约束"
        )
    
    # ========================================
    # 辅助方法
    # ========================================
    
    def create_claim(
        self,
        claim_type: ClaimType,
        confidence: float,
        direction: str | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> Claim:
        """创建 Claim 的辅助方法"""
        return Claim(
            strategy_id=self.strategy_id,
            claim_type=claim_type,
            confidence=confidence,
            validity_window=self.validity_window,
            direction=direction,
            constraints=constraints or {},
        )
    
    def mute(self) -> None:
        """静默此证人"""
        self._status = WitnessStatus.MUTED
    
    def activate(self) -> None:
        """激活此证人"""
        self._status = WitnessStatus.ACTIVE
    
    @property
    def is_active(self) -> bool:
        """是否激活"""
        return self._status == WitnessStatus.ACTIVE
    
    @property
    def is_core_witness(self) -> bool:
        """是否为核心证人"""
        return self.tier == WitnessTier.TIER_1
    
    @property
    def has_veto_power(self) -> bool:
        """是否有否决权"""
        return self.tier == WitnessTier.TIER_3
