"""
BTC 自动交易系统 — 多用户执行器

并行执行多用户交易。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.logging import get_logger
from src.common.utils import utc_now
from src.user.context import TradingSignal, UserContext, UserExecutionResult
from src.user.manager import UserManager
from src.user.models import User, UserExchangeConfig, UserRiskState

logger = get_logger(__name__)


@dataclass
class BroadcastResult:
    """广播结果"""
    signal_id: str
    total_users: int
    success_count: int
    failed_count: int
    skipped_count: int
    results: dict[str, UserExecutionResult] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "total_users": self.total_users,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "timestamp": self.timestamp.isoformat(),
        }


class MultiUserExecutor:
    """
    多用户并行执行器
    
    功能：
    - 管理所有用户的执行上下文
    - 并行广播交易信号
    - 异常隔离（单用户失败不影响其他）
    """
    
    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager
        self._contexts: dict[str, UserContext] = {}
        self._initialized = False
        self._execution_timeout = 30.0  # 单用户执行超时
    
    @property
    def active_count(self) -> int:
        """活跃用户数"""
        return len([c for c in self._contexts.values() if c.is_tradeable])
    
    @property
    def total_count(self) -> int:
        """总用户数"""
        return len(self._contexts)
    
    async def initialize_all(self) -> int:
        """
        初始化所有可交易用户
        
        Returns:
            成功初始化的用户数
        """
        # 获取可交易用户
        tradeable_users = await self.user_manager.get_tradeable_users()
        
        success_count = 0
        
        for user, config, risk_state in tradeable_users:
            try:
                context = UserContext(user, config, risk_state)
                
                if await context.initialize():
                    self._contexts[user.user_id] = context
                    success_count += 1
                else:
                    logger.warning(f"用户初始化失败: {user.user_id}")
                    
            except Exception as e:
                logger.error(f"用户初始化异常: {user.user_id}, error={e}")
        
        self._initialized = True
        logger.info(f"多用户执行器已初始化: {success_count}/{len(tradeable_users)} 用户")
        return success_count
    
    async def shutdown_all(self) -> None:
        """关闭所有用户上下文"""
        for context in self._contexts.values():
            try:
                await context.shutdown()
            except Exception as e:
                logger.error(f"用户关闭异常: {context.user_id}, error={e}")
        
        self._contexts.clear()
        self._initialized = False
        logger.info("多用户执行器已关闭")
    
    async def broadcast_signal(self, signal: TradingSignal) -> BroadcastResult:
        """
        广播交易信号给所有用户
        
        Args:
            signal: 交易信号
        
        Returns:
            广播结果
        """
        if not self._initialized:
            await self.initialize_all()
        
        tradeable_contexts = [c for c in self._contexts.values() if c.is_tradeable]
        
        result = BroadcastResult(
            signal_id=signal.signal_id,
            total_users=len(self._contexts),
            success_count=0,
            failed_count=0,
            skipped_count=len(self._contexts) - len(tradeable_contexts),
        )
        
        if not tradeable_contexts:
            logger.warning(f"无可交易用户，信号 {signal.signal_id} 跳过")
            return result
        
        # 并行执行
        tasks = []
        for context in tradeable_contexts:
            task = self._execute_with_timeout(context, signal)
            tasks.append((context.user_id, task))
        
        # 等待所有任务完成
        for user_id, task in tasks:
            try:
                exec_result = await task
                result.results[user_id] = exec_result
                
                if exec_result.success:
                    result.success_count += 1
                else:
                    result.failed_count += 1
                    
            except Exception as e:
                logger.error(f"用户 {user_id} 执行异常: {e}")
                result.results[user_id] = UserExecutionResult(
                    user_id=user_id,
                    signal_id=signal.signal_id,
                    success=False,
                    error=str(e),
                )
                result.failed_count += 1
        
        logger.info(
            f"信号 {signal.signal_id} 广播完成: "
            f"成功={result.success_count}, 失败={result.failed_count}, 跳过={result.skipped_count}"
        )
        
        return result
    
    async def _execute_with_timeout(
        self,
        context: UserContext,
        signal: TradingSignal,
    ) -> UserExecutionResult:
        """带超时的执行"""
        try:
            return await asyncio.wait_for(
                context.execute_signal(signal),
                timeout=self._execution_timeout,
            )
        except asyncio.TimeoutError:
            return UserExecutionResult(
                user_id=context.user_id,
                signal_id=signal.signal_id,
                success=False,
                error="执行超时",
            )
    
    async def add_user(self, user_id: str) -> bool:
        """
        添加用户
        
        Args:
            user_id: 用户 ID
        
        Returns:
            是否成功
        """
        if user_id in self._contexts:
            return True
        
        user = await self.user_manager.get_user(user_id)
        if not user or not user.is_active:
            return False
        
        config = await self.user_manager.get_exchange_config(user_id)
        if not config or not config.is_valid:
            return False
        
        risk_state = await self.user_manager.get_or_create_risk_state(user_id)
        if risk_state.is_locked:
            return False
        
        context = UserContext(user, config, risk_state)
        
        if await context.initialize():
            self._contexts[user_id] = context
            logger.info(f"用户已添加: {user_id}")
            return True
        
        return False
    
    async def remove_user(self, user_id: str) -> bool:
        """
        移除用户
        
        Args:
            user_id: 用户 ID
        
        Returns:
            是否成功
        """
        context = self._contexts.pop(user_id, None)
        if context:
            await context.shutdown()
            logger.info(f"用户已移除: {user_id}")
            return True
        return False
    
    async def refresh_user(self, user_id: str) -> bool:
        """
        刷新用户（重新加载配置）
        
        Args:
            user_id: 用户 ID
        
        Returns:
            是否成功
        """
        await self.remove_user(user_id)
        return await self.add_user(user_id)
    
    def get_user_status(self, user_id: str) -> dict[str, Any] | None:
        """获取用户状态"""
        context = self._contexts.get(user_id)
        if not context:
            return None
        
        return {
            "user_id": user_id,
            "is_initialized": context.is_initialized,
            "is_tradeable": context.is_tradeable,
            "risk_state": context.risk_state.to_dict(),
        }
    
    def get_all_status(self) -> dict[str, Any]:
        """获取所有用户状态"""
        return {
            "total_users": self.total_count,
            "active_users": self.active_count,
            "users": {
                user_id: self.get_user_status(user_id)
                for user_id in self._contexts
            },
        }
    
    async def close_all_positions(self, symbol: str = "BTCUSDT") -> dict[str, UserExecutionResult]:
        """
        关闭所有用户的仓位
        
        Args:
            symbol: 交易对
        
        Returns:
            用户 ID -> 执行结果
        """
        results = {}
        
        for user_id, context in self._contexts.items():
            try:
                result = await context.close_position(symbol)
                results[user_id] = result
            except Exception as e:
                results[user_id] = UserExecutionResult(
                    user_id=user_id,
                    signal_id="close_all",
                    success=False,
                    error=str(e),
                )
        
        return results
