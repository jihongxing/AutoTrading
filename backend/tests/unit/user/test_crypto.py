"""
API Key 加密单元测试
"""

import pytest

from src.user.crypto import (
    ApiKeyCrypto,
    decrypt_api_key,
    encrypt_api_key,
    get_crypto,
)


class TestApiKeyCrypto:
    """API Key 加密测试"""
    
    def test_encrypt_decrypt(self):
        crypto = ApiKeyCrypto()
        
        original = "my-secret-api-key-12345"
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)
        
        assert encrypted != original
        assert decrypted == original
    
    def test_encrypt_different_each_time(self):
        crypto = ApiKeyCrypto()
        
        original = "my-secret-api-key"
        encrypted1 = crypto.encrypt(original)
        encrypted2 = crypto.encrypt(original)
        
        # 由于随机 nonce，每次加密结果不同
        assert encrypted1 != encrypted2
        
        # 但都能正确解密
        assert crypto.decrypt(encrypted1) == original
        assert crypto.decrypt(encrypted2) == original
    
    def test_decrypt_invalid(self):
        crypto = ApiKeyCrypto()
        
        # 无效的加密数据应返回空字符串
        result = crypto.decrypt("")
        assert result == ""
    
    def test_empty_string(self):
        crypto = ApiKeyCrypto()
        
        encrypted = crypto.encrypt("")
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == ""


class TestModuleFunctions:
    """模块级函数测试"""
    
    def test_get_crypto_singleton(self):
        crypto1 = get_crypto()
        crypto2 = get_crypto()
        
        assert crypto1 is crypto2
    
    def test_encrypt_decrypt_functions(self):
        original = "test-api-key"
        
        encrypted = encrypt_api_key(original)
        decrypted = decrypt_api_key(encrypted)
        
        assert decrypted == original
