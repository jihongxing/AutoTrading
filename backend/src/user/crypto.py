"""
BTC 自动交易系统 — API Key 加密

使用 AES-256-GCM 加密存储敏感信息。
"""

import base64
import hashlib
import os
from typing import Any

from src.common.logging import get_logger

logger = get_logger(__name__)


class ApiKeyCrypto:
    """
    API Key 加密工具
    
    使用 AES-256-GCM 加密，提供认证加密。
    """
    
    def __init__(self, master_key: str | bytes | None = None):
        """
        初始化加密器
        
        Args:
            master_key: 主密钥，可以是字符串或字节。
                       如果为 None，从环境变量 ENCRYPTION_KEY 读取。
        """
        if master_key is None:
            master_key = os.environ.get("ENCRYPTION_KEY", "")
        
        if isinstance(master_key, str):
            # 使用 SHA-256 派生 32 字节密钥
            self._key = hashlib.sha256(master_key.encode()).digest()
        else:
            self._key = master_key[:32].ljust(32, b'\0')
        
        self._cipher: Any = None
        self._init_cipher()
    
    def _init_cipher(self) -> None:
        """初始化加密器"""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            self._cipher = AESGCM(self._key)
        except ImportError:
            logger.warning("cryptography 未安装，使用简单编码（不安全）")
            self._cipher = None
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串
        
        Args:
            plaintext: 明文
        
        Returns:
            Base64 编码的密文（包含 nonce）
        """
        if not plaintext:
            return ""
        
        if self._cipher is None:
            # 降级：Base64 编码（不安全，仅用于开发）
            return base64.b64encode(plaintext.encode()).decode()
        
        # 生成随机 nonce（12 字节）
        nonce = os.urandom(12)
        
        # 加密
        ciphertext = self._cipher.encrypt(nonce, plaintext.encode(), None)
        
        # 组合 nonce + ciphertext 并 Base64 编码
        return base64.b64encode(nonce + ciphertext).decode()
    
    def decrypt(self, encrypted: str) -> str:
        """
        解密字符串
        
        Args:
            encrypted: Base64 编码的密文
        
        Returns:
            明文
        """
        if not encrypted:
            return ""
        
        if self._cipher is None:
            # 降级：Base64 解码
            return base64.b64decode(encrypted).decode()
        
        # Base64 解码
        data = base64.b64decode(encrypted)
        
        # 分离 nonce 和 ciphertext
        nonce = data[:12]
        ciphertext = data[12:]
        
        # 解密
        plaintext = self._cipher.decrypt(nonce, ciphertext, None)
        return plaintext.decode()
    
    def is_secure(self) -> bool:
        """是否使用安全加密"""
        return self._cipher is not None


# 全局加密器实例
_crypto: ApiKeyCrypto | None = None


def get_crypto() -> ApiKeyCrypto:
    """获取全局加密器"""
    global _crypto
    if _crypto is None:
        _crypto = ApiKeyCrypto()
    return _crypto


def encrypt_api_key(api_key: str) -> str:
    """加密 API Key"""
    return get_crypto().encrypt(api_key)


def decrypt_api_key(encrypted: str) -> str:
    """解密 API Key"""
    return get_crypto().decrypt(encrypted)
