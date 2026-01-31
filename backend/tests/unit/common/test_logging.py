"""日志工具测试"""

import json
import logging
import pytest

from src.common.logging import JSONFormatter, get_logger, LoggerAdapter


class TestJSONFormatter:
    """JSON 格式化器测试"""
    
    def test_format_basic(self):
        """验证基本格式化"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="测试消息",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "测试消息"
        assert "timestamp" in data
        assert data["location"]["line"] == 10
    
    def test_format_with_exception(self):
        """验证异常格式化"""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("测试异常")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="发生错误",
            args=(),
            exc_info=exc_info,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "exception" in data
        assert "ValueError" in data["exception"]


class TestGetLogger:
    """get_logger 函数测试"""
    
    def test_get_logger_basic(self):
        """验证基本获取"""
        logger = get_logger("test_basic")
        assert logger.name == "test_basic"
        assert logger.level == logging.INFO
    
    def test_get_logger_custom_level(self):
        """验证自定义级别"""
        logger = get_logger("test_debug", level=logging.DEBUG)
        assert logger.level == logging.DEBUG
    
    def test_get_logger_reuse(self):
        """验证重复获取返回同一实例"""
        logger1 = get_logger("test_reuse")
        logger2 = get_logger("test_reuse")
        assert logger1 is logger2
        assert len(logger1.handlers) == 1  # 不重复添加 handler
    
    def test_get_logger_no_json(self):
        """验证非 JSON 格式"""
        logger = get_logger("test_plain", use_json=False)
        assert logger.handlers[0].formatter is not None
        assert not isinstance(logger.handlers[0].formatter, JSONFormatter)


class TestLoggerAdapter:
    """LoggerAdapter 测试"""
    
    def test_adapter_extra(self):
        """验证额外字段传递"""
        base_logger = get_logger("test_adapter_base")
        adapter = LoggerAdapter(base_logger, {"request_id": "r123"})
        
        # 验证 adapter 可以正常使用
        assert adapter.extra == {"request_id": "r123"}
