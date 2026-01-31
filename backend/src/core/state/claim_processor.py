"""
BTC 自动交易系统 — Claim 处理器

处理策略 Claim，验证有效性，调用风控检查。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.common.enums import ClaimType, RiskLevel, SystemState
from src.common.exceptions import InvalidClaimError
from src.common.logging import get_logger
from src.common.models import Claim, RiskCheckResult
from src.common.utils import utc_now
from src.core.risk.base import RiskContext
from src.core.risk.engine import RiskControlEngine

from .machine import StateMachine
from .regime import RegimeManager, TradeRegime

logger = get_logger(__name__)


@dataclass
class ProcessResult:
    """Claim 处理结果"""
    success: bool
    claim: Claim
    state_changed: bool
    new_state: SystemState | None
    risk_result: RiskCheckResult | None
    regime: TradeRegime | None
    reason: str
    timestamp: datetime


class ClaimProcessor:
    """
    Claim 处理器
    
    处理策略 Claim，验证有效性，调用风控检查，决定状态转换。
    """
    
    def __init__(
        self,
        state_machine: StateMachine,
        risk_engine: RiskControlEngine,
        regime_manager: RegimeManager,
    ):
        self.state_machine = state_machine
        self.risk_engine = risk_engine
        self.regime_manager = regime_manager
    
    async def process_claim(
        self,
        claim: Claim,
        risk_context: RiskContext,
    ) -> ProcessResult:
        """
        处理策略 Claim
        
        Args:
            claim: 策略声明
            risk_context: 风控上下文
        
        Returns:
            处理结果
        """
        # 1. 验证 Claim 有效性
        validation_error = self._validate_claim(claim)
        if validation_error:
            logger.warning(f"Claim 验证失败: {validation_error}")
            return ProcessResult(
                success=False,
                claim=claim,
                state_changed=False,
                new_state=None,
                risk_result=None,
                regime=None,
                reason=validation_error,
                timestamp=utc_now(),
            )
        
        # 2. 检查当前状态是否允许处理 Claim
        if self.state_machine.current_state != SystemState.OBSERVING:
            return ProcessResult(
                success=False,
                claim=claim,
                state_changed=False,
                new_state=None,
                risk_result=None,
                regime=None,
                reason=f"当前状态 {self.state_machine.current_state.value} 不接受 Claim",
                timestamp=utc_now(),
            )
        
        # 3. 根据 Claim 类型处理
        if claim.claim_type == ClaimType.MARKET_NOT_ELIGIBLE:
            return ProcessResult(
                success=True,
                claim=claim,
                state_changed=False,
                new_state=None,
                risk_result=None,
                regime=None,
                reason="市场不适合交易",
                timestamp=utc_now(),
            )
        
        if claim.claim_type == ClaimType.EXECUTION_VETO:
            return ProcessResult(
                success=True,
                claim=claim,
                state_changed=False,
                new_state=None,
                risk_result=None,
                regime=None,
                reason="执行否决",
                timestamp=utc_now(),
            )
        
        # 4. 调用风控检查
        risk_result = await self.risk_engine.check_permission(risk_context)
        
        if not risk_result.approved:
            logger.warning(f"风控拒绝: {risk_result.reason}")
            
            # 风控锁定
            if risk_result.level == RiskLevel.RISK_LOCKED:
                await self.state_machine.force_lock(risk_result.reason or "风控触发")
            
            return ProcessResult(
                success=False,
                claim=claim,
                state_changed=risk_result.level == RiskLevel.RISK_LOCKED,
                new_state=SystemState.RISK_LOCKED if risk_result.level == RiskLevel.RISK_LOCKED else None,
                risk_result=risk_result,
                regime=None,
                reason=risk_result.reason or "风控拒绝",
                timestamp=utc_now(),
            )
        
        # 5. 设置交易范式
        regime = self._determine_regime(claim)
        if regime != TradeRegime.NO_REGIME:
            self.regime_manager.set_regime(regime, claim.confidence)
        
        # 6. 状态转换到 ELIGIBLE
        transition_result = await self.state_machine.become_eligible(
            reason=f"Claim 批准: {claim.claim_type.value}"
        )
        
        if not transition_result.success:
            return ProcessResult(
                success=False,
                claim=claim,
                state_changed=False,
                new_state=None,
                risk_result=risk_result,
                regime=regime,
                reason=transition_result.error or "状态转换失败",
                timestamp=utc_now(),
            )
        
        logger.info(
            f"Claim 处理成功: {claim.strategy_id}, 范式: {regime.value}",
            extra={"strategy_id": claim.strategy_id, "regime": regime.value},
        )
        
        return ProcessResult(
            success=True,
            claim=claim,
            state_changed=True,
            new_state=SystemState.ELIGIBLE,
            risk_result=risk_result,
            regime=regime,
            reason="Claim 批准，进入 ELIGIBLE 状态",
            timestamp=utc_now(),
        )
    
    def _validate_claim(self, claim: Claim) -> str | None:
        """
        验证 Claim 有效性
        
        Returns:
            错误信息，如果有效则返回 None
        """
        # 检查时间戳
        age = (utc_now() - claim.timestamp).total_seconds()
        if age > claim.validity_window:
            return f"Claim 已过期: {age:.0f}s > {claim.validity_window}s"
        
        # 检查置信度
        if claim.confidence < 0.5:
            return f"置信度过低: {claim.confidence:.2%}"
        
        # 检查 Claim 类型
        if claim.claim_type not in ClaimType:
            return f"无效的 Claim 类型: {claim.claim_type}"
        
        return None
    
    def _determine_regime(self, claim: Claim) -> TradeRegime:
        """根据 Claim 确定交易范式"""
        # 从 Claim 约束中获取范式
        regime_str = claim.constraints.get("regime")
        if regime_str:
            try:
                return TradeRegime(regime_str)
            except ValueError:
                pass
        
        # 根据 Claim 类型推断
        if claim.claim_type == ClaimType.REGIME_MATCHED:
            return TradeRegime.VOLATILITY_EXPANSION
        
        return TradeRegime.NO_REGIME
