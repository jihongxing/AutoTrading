"""
BTC 自动交易系统 — 状态机服务

整合状态机、Claim 处理、风控，提供统一接口。
"""

from typing import Any

from src.common.enums import SystemState
from src.common.logging import get_logger
from src.common.models import Claim
from src.core.risk.base import RiskContext
from src.core.risk.engine import RiskControlEngine

from .claim_processor import ClaimProcessor, ProcessResult
from .machine import StateMachine
from .regime import RegimeManager, RegimeOutput, TradeRegime
from .storage import StateStorage
from .transitions import TransitionRecord

logger = get_logger(__name__)


class StateMachineService:
    """
    状态机服务
    
    整合状态机、Claim 处理、风控，对外提供统一接口。
    """
    
    def __init__(
        self,
        risk_engine: RiskControlEngine | None = None,
    ):
        self.state_machine = StateMachine()
        self.risk_engine = risk_engine or RiskControlEngine()
        self.regime_manager = RegimeManager()
        self.storage = StateStorage()
        self.claim_processor = ClaimProcessor(
            state_machine=self.state_machine,
            risk_engine=self.risk_engine,
            regime_manager=self.regime_manager,
        )
    
    # ========================================
    # 状态查询
    # ========================================
    
    def get_current_state(self) -> SystemState:
        """获取当前状态"""
        return self.state_machine.current_state
    
    def is_trading_allowed(self) -> bool:
        """是否允许交易"""
        return self.state_machine.is_trading_allowed
    
    def is_locked(self) -> bool:
        """是否被锁定"""
        return self.state_machine.is_locked
    
    def get_current_regime(self) -> TradeRegime | None:
        """获取当前交易范式"""
        if self.regime_manager.is_valid:
            return self.regime_manager.current_regime
        return None
    
    def get_regime_output(self) -> RegimeOutput | None:
        """获取范式输出"""
        return self.regime_manager.get_output()
    
    def get_state_history(self, limit: int = 100) -> list[TransitionRecord]:
        """获取状态历史"""
        return self.state_machine.get_transition_history(limit)
    
    # ========================================
    # Claim 处理
    # ========================================
    
    async def submit_claim(
        self,
        claim: Claim,
        risk_context: RiskContext,
    ) -> ProcessResult:
        """
        提交策略 Claim
        
        Args:
            claim: 策略声明
            risk_context: 风控上下文
        
        Returns:
            处理结果
        """
        result = await self.claim_processor.process_claim(claim, risk_context)
        
        # 保存状态
        if result.state_changed and result.new_state:
            await self.storage.save_state(
                state=result.new_state,
                entered_at=self.state_machine._state_entered_at,
                metadata={"claim_id": claim.strategy_id},
            )
        
        return result
    
    # ========================================
    # 状态转换
    # ========================================
    
    async def initialize(self) -> bool:
        """初始化系统"""
        if self.state_machine.current_state != SystemState.SYSTEM_INIT:
            logger.warning("系统已初始化")
            return False
        
        result = await self.state_machine.initialize_complete()
        if result.success:
            await self.storage.save_state(
                state=SystemState.OBSERVING,
                entered_at=self.state_machine._state_entered_at,
            )
        return result.success
    
    async def start_trading(self, reason: str) -> bool:
        """开始交易"""
        result = await self.state_machine.start_trading(reason)
        if result.success:
            await self.storage.save_state(
                state=SystemState.ACTIVE_TRADING,
                entered_at=self.state_machine._state_entered_at,
            )
        return result.success
    
    async def complete_trading(self, reason: str) -> bool:
        """完成交易"""
        result = await self.state_machine.complete_trading(reason)
        if result.success:
            self.regime_manager.clear_regime()
            await self.storage.save_state(
                state=SystemState.COOLDOWN,
                entered_at=self.state_machine._state_entered_at,
            )
        return result.success
    
    async def complete_cooldown(self) -> bool:
        """完成冷却"""
        result = await self.state_machine.complete_cooldown()
        if result.success:
            await self.storage.save_state(
                state=SystemState.OBSERVING,
                entered_at=self.state_machine._state_entered_at,
            )
        return result.success
    
    async def force_lock(self, reason: str) -> bool:
        """强制锁定"""
        result = await self.state_machine.force_lock(reason)
        if result.success:
            self.regime_manager.clear_regime()
            await self.storage.save_state(
                state=SystemState.RISK_LOCKED,
                entered_at=self.state_machine._state_entered_at,
                metadata={"reason": reason},
            )
        return result.success
    
    async def start_recovery(self, reason: str) -> bool:
        """开始恢复"""
        result = await self.state_machine.start_recovery(reason)
        if result.success:
            await self.storage.save_state(
                state=SystemState.RECOVERY,
                entered_at=self.state_machine._state_entered_at,
            )
        return result.success
    
    async def complete_recovery(self) -> bool:
        """完成恢复"""
        result = await self.state_machine.complete_recovery()
        if result.success:
            await self.storage.save_state(
                state=SystemState.OBSERVING,
                entered_at=self.state_machine._state_entered_at,
            )
        return result.success
    
    async def cancel_eligible(self, reason: str) -> bool:
        """取消允许交易状态"""
        result = await self.state_machine.cancel_eligible(reason)
        if result.success:
            self.regime_manager.clear_regime()
            await self.storage.save_state(
                state=SystemState.OBSERVING,
                entered_at=self.state_machine._state_entered_at,
            )
        return result.success
