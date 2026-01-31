"""
BTC 自动交易系统 — 重试装饰器

提供指数退避和固定间隔重试策略。
"""

import asyncio
import functools
import inspect
import random
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from .logging import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential: bool = True,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    重试装饰器（支持同步和异步函数）
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential: 是否使用指数退避
        jitter: 是否添加随机抖动
        exceptions: 需要重试的异常类型
    
    Returns:
        装饰器函数
    """
    
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)  # type: ignore
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.warning(
                            f"重试耗尽: {func.__name__}, 尝试 {attempt + 1}/{max_retries + 1}",
                            extra={"error": str(e)},
                        )
                        raise
                    
                    delay = _calculate_delay(
                        attempt, base_delay, max_delay, exponential, jitter
                    )
                    
                    logger.info(
                        f"重试: {func.__name__}, 尝试 {attempt + 1}/{max_retries + 1}, "
                        f"延迟 {delay:.2f}s",
                        extra={"error": str(e)},
                    )
                    
                    await asyncio.sleep(delay)
            
            # 不应该到达这里
            raise last_exception  # type: ignore
        
        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            import time
            
            last_exception: Exception | None = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.warning(
                            f"重试耗尽: {func.__name__}, 尝试 {attempt + 1}/{max_retries + 1}",
                            extra={"error": str(e)},
                        )
                        raise
                    
                    delay = _calculate_delay(
                        attempt, base_delay, max_delay, exponential, jitter
                    )
                    
                    logger.info(
                        f"重试: {func.__name__}, 尝试 {attempt + 1}/{max_retries + 1}, "
                        f"延迟 {delay:.2f}s",
                        extra={"error": str(e)},
                    )
                    
                    time.sleep(delay)
            
            raise last_exception  # type: ignore
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


def _calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential: bool,
    jitter: bool,
) -> float:
    """计算重试延迟"""
    if exponential:
        delay = base_delay * (2 ** attempt)
    else:
        delay = base_delay
    
    delay = min(delay, max_delay)
    
    if jitter:
        delay = delay * (0.5 + random.random())
    
    return delay
