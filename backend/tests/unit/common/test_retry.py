"""重试装饰器测试"""

import asyncio
import pytest
from unittest.mock import MagicMock

from src.common.retry import retry_with_backoff, _calculate_delay


class TestCalculateDelay:
    """延迟计算测试"""
    
    def test_fixed_delay(self):
        """验证固定延迟"""
        delay = _calculate_delay(
            attempt=0,
            base_delay=1.0,
            max_delay=60.0,
            exponential=False,
            jitter=False,
        )
        assert delay == 1.0
    
    def test_exponential_delay(self):
        """验证指数退避"""
        delay0 = _calculate_delay(0, 1.0, 60.0, True, False)
        delay1 = _calculate_delay(1, 1.0, 60.0, True, False)
        delay2 = _calculate_delay(2, 1.0, 60.0, True, False)
        
        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0
    
    def test_max_delay_cap(self):
        """验证最大延迟限制"""
        delay = _calculate_delay(10, 1.0, 5.0, True, False)
        assert delay == 5.0
    
    def test_jitter(self):
        """验证抖动"""
        delays = [
            _calculate_delay(0, 1.0, 60.0, False, True)
            for _ in range(10)
        ]
        # 抖动应该产生不同的值
        assert len(set(delays)) > 1


class TestRetrySync:
    """同步重试测试"""
    
    def test_success_no_retry(self):
        """验证成功时不重试"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "ok"
        
        result = success_func()
        assert result == "ok"
        assert call_count == 1
    
    def test_retry_then_success(self):
        """验证重试后成功"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("临时错误")
            return "ok"
        
        result = flaky_func()
        assert result == "ok"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """验证重试耗尽"""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("永久错误")
        
        with pytest.raises(ValueError, match="永久错误"):
            always_fail()
        
        assert call_count == 3  # 初始 + 2 次重试
    
    def test_specific_exception(self):
        """验证只重试指定异常"""
        call_count = 0
        
        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            exceptions=(ValueError,)
        )
        def specific_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("不重试此异常")
        
        with pytest.raises(TypeError):
            specific_error()
        
        assert call_count == 1  # 不重试


class TestRetryAsync:
    """异步重试测试"""
    
    @pytest.mark.asyncio
    async def test_async_success(self):
        """验证异步成功"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def async_success():
            nonlocal call_count
            call_count += 1
            return "async_ok"
        
        result = await async_success()
        assert result == "async_ok"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_retry(self):
        """验证异步重试"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def async_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("临时错误")
            return "ok"
        
        result = await async_flaky()
        assert result == "ok"
        assert call_count == 2
