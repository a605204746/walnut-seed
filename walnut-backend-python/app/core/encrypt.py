"""加解密工具（基于 cryptography 实现）。

- AES 默认 ``AES/ECB/PKCS5Padding``，密钥长度 16/24/32；
- RSA 默认 ``RSA/ECB/PKCS1Padding``，公私钥为 PKCS#8/X.509 DER 的 Base64；
- SM2/SM4 为可选国密（需安装 ``gmssl`` extra）。

接口加解密流程：RSA 包裹一次性随机 AES 密钥，AES 加解密 JSON 体。
"""

import base64
import hashlib
import secrets

from app.common.enums import HttpStatus
from app.core.exceptions import ServiceException

try:
    from cryptography.hazmat.primitives import padding as _sym_padding
    from cryptography.hazmat.primitives import serialization as _serialization
    from cryptography.hazmat.primitives.asymmetric import padding as _asym_padding
    from cryptography.hazmat.primitives.ciphers import Cipher as _Cipher
    from cryptography.hazmat.primitives.ciphers import algorithms as _algorithms
    from cryptography.hazmat.primitives.ciphers import modes as _modes

    _CRYPTO_AVAILABLE = True
except Exception:  # pragma: no cover
    _CRYPTO_AVAILABLE = False


def _require_crypto() -> None:
    if not _CRYPTO_AVAILABLE:
        raise ServiceException("cryptography 库未安装，无法执行加解密", code=HttpStatus.ERROR)


# ==================== Base64 ====================
def encrypt_by_base64(data: str) -> str:
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def decrypt_by_base64(data: str) -> str:
    return base64.b64decode(data.encode("utf-8")).decode("utf-8")


# ==================== AES / ECB / PKCS5(PKCS7) ====================
def _check_aes_key(password: str) -> bytes:
    if not password:
        raise ServiceException("AES需要传入秘钥信息")
    if len(password) not in (16, 24, 32):
        raise ServiceException("AES秘钥长度要求为16位、24位、32位")
    return password.encode("utf-8")


def encrypt_by_aes(data: str, password: str) -> str:
    """AES/ECB/PKCS5Padding 加密，输出 Base64。"""
    _require_crypto()
    key = _check_aes_key(password)
    padder = _sym_padding.PKCS7(128).padder()
    padded = padder.update(data.encode("utf-8")) + padder.finalize()
    encryptor = _Cipher(_algorithms.AES(key), _modes.ECB()).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode("utf-8")


def decrypt_by_aes(data: str, password: str) -> str:
    """AES/ECB/PKCS5Padding 解密，输入 Base64。"""
    _require_crypto()
    key = _check_aes_key(password)
    ciphertext = base64.b64decode(data.encode("utf-8"))
    decryptor = _Cipher(_algorithms.AES(key), _modes.ECB()).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = _sym_padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()
    return plaintext.decode("utf-8")


# ==================== RSA / PKCS1v15 ====================
def _load_public_key(public_key_b64: str):
    if not public_key_b64:
        raise ServiceException("RSA需要传入公钥进行加密")
    return _serialization.load_der_public_key(base64.b64decode(public_key_b64))


def _load_private_key(private_key_b64: str):
    if not private_key_b64:
        raise ServiceException("RSA需要传入私钥进行解密")
    return _serialization.load_der_private_key(base64.b64decode(private_key_b64), password=None)


def encrypt_by_rsa(data: str, public_key: str) -> str:
    """RSA/PKCS1v15 加密（公钥），输出 Base64。超长数据自动分段。"""
    _require_crypto()
    pub = _load_public_key(public_key)
    max_chunk = pub.key_size // 8 - 11
    raw = data.encode("utf-8")
    chunks = [raw[i : i + max_chunk] for i in range(0, len(raw), max_chunk)] or [b""]
    encrypted = b"".join(pub.encrypt(chunk, _asym_padding.PKCS1v15()) for chunk in chunks)
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_by_rsa(data: str, private_key: str) -> str:
    """RSA/PKCS1v15 解密（私钥），输入 Base64。超长数据自动分段。"""
    _require_crypto()
    priv = _load_private_key(private_key)
    chunk_size = priv.key_size // 8
    raw = base64.b64decode(data.encode("utf-8"))
    chunks = [raw[i : i + chunk_size] for i in range(0, len(raw), chunk_size)] or [b""]
    decrypted = b"".join(priv.decrypt(chunk, _asym_padding.PKCS1v15()) for chunk in chunks)
    return decrypted.decode("utf-8")


# ==================== 摘要 ====================
def encrypt_by_md5(data: str) -> str:
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def encrypt_by_sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ==================== 国密（可选） ====================
def encrypt_by_sm4(data: str, password: str) -> str:
    if not password or len(password) != 16:
        raise ServiceException("SM4秘钥长度要求为16位")
    try:
        from gmssl.sm4 import SM4_ENCRYPT, CryptSM4  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ServiceException("SM4 需安装 gmssl（uv sync --extra gm）") from exc
    crypt = CryptSM4()
    crypt.set_key(password.encode("utf-8"), SM4_ENCRYPT)
    return base64.b64encode(crypt.crypt_ecb(data.encode("utf-8"))).decode("utf-8")


def random_string(length: int = 32) -> str:
    """生成随机字符串（用于一次性 AES 密钥）。"""
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
