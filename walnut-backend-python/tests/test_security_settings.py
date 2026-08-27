"""启动密钥校验 validate_security_settings 回归测试。

锁定的整改行为：
- prod 弱 SECRET_KEY（空/含 change-me/长度 <32 字节）-> RuntimeError 拒绝启动；dev 仅告警放行；
- prod 命中已知坏 RSA 密钥前缀（RuoYi 出厂密钥，KNOWN_BAD_* 常量）-> RuntimeError；
- 密钥为空/无效 -> settings.API_DECRYPT_ENABLED 自动置 False（安全降级为明文，绝不带假密钥运行）；
- dev 已知坏密钥不崩溃、同样降级。

settings 为单例：全部通过 monkeypatch 修改并在用例后自动还原，避免污染其他测试。
"""

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.common.enums import EnvironmentEnum
from app.config.setting import settings
from app.init_app import (
    KNOWN_BAD_RSA_PRIVATE_PREFIX,
    KNOWN_BAD_RSA_PUBLIC_PREFIX,
    validate_security_settings,
)

STRONG_SECRET = "unit-test-strong-secret-key-0123456789abcdef"  # ≥32 字节且不含 change-me


@pytest.fixture(scope="module")
def valid_rsa_pair():
    """生成一对可通过 _rsa_keys_loadable 校验的 1024 位 RSA 密钥（base64 DER）。"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    private = base64.b64encode(
        key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    ).decode()
    public = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
    return public, private


@pytest.fixture
def controlled_env(monkeypatch):
    """受控初始值（monkeypatch 自动恢复，用例间互不污染）。"""
    monkeypatch.setattr(settings, "ENVIRONMENT", EnvironmentEnum.DEV)
    monkeypatch.setattr(settings, "SECRET_KEY", STRONG_SECRET)
    monkeypatch.setattr(settings, "API_DECRYPT_ENABLED", True)
    monkeypatch.setattr(settings, "API_DECRYPT_PUBLIC_KEY", "")
    monkeypatch.setattr(settings, "API_DECRYPT_PRIVATE_KEY", "")
    return settings


# ---------- SECRET_KEY ----------


@pytest.mark.parametrize(
    "weak_secret",
    [
        "",  # 空
        "change-me",  # 含 change-me
        "walnut-seed-change-me-32-bytes-min-jwt-secret-0123456789",  # 代码默认占位值（含 change-me）
        "short-key",  # 长度不足 32 字节
        "a" * 31,  # 31 字节，临界以下
    ],
)
def test_prod_weak_secret_refuses_to_start(controlled_env, weak_secret):
    controlled_env.ENVIRONMENT = EnvironmentEnum.PROD
    controlled_env.SECRET_KEY = weak_secret
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_security_settings()


def test_dev_weak_secret_warns_but_passes(controlled_env):
    controlled_env.SECRET_KEY = "change-me"
    validate_security_settings()  # dev 仅告警，不抛错


def test_prod_strong_secret_passes(controlled_env):
    controlled_env.ENVIRONMENT = EnvironmentEnum.PROD
    controlled_env.SECRET_KEY = "a" * 32  # 恰好 32 字节临界值
    validate_security_settings()  # SECRET_KEY 校验通过（RSA 为空走降级，不抛错）


# ---------- RSA 已知坏密钥 ----------


def test_prod_known_bad_public_key_refuses_to_start(controlled_env):
    controlled_env.ENVIRONMENT = EnvironmentEnum.PROD
    controlled_env.API_DECRYPT_PUBLIC_KEY = KNOWN_BAD_RSA_PUBLIC_PREFIX + "AAAA"
    with pytest.raises(RuntimeError, match="RSA"):
        validate_security_settings()


def test_prod_known_bad_private_key_refuses_to_start(controlled_env):
    controlled_env.ENVIRONMENT = EnvironmentEnum.PROD
    controlled_env.API_DECRYPT_PRIVATE_KEY = KNOWN_BAD_RSA_PRIVATE_PREFIX + "AAAA"
    with pytest.raises(RuntimeError, match="RSA"):
        validate_security_settings()


def test_dev_known_bad_keys_degrade_not_crash(controlled_env):
    controlled_env.API_DECRYPT_PUBLIC_KEY = KNOWN_BAD_RSA_PUBLIC_PREFIX + "AAAA"
    controlled_env.API_DECRYPT_PRIVATE_KEY = KNOWN_BAD_RSA_PRIVATE_PREFIX + "AAAA"
    validate_security_settings()  # dev 不拒绝启动
    assert settings.API_DECRYPT_ENABLED is False  # 但强制停用接口加解密


# ---------- 空 / 无效密钥降级 ----------


def test_empty_keys_disable_api_decrypt(controlled_env):
    validate_security_settings()
    assert settings.API_DECRYPT_ENABLED is False


def test_invalid_keys_disable_api_decrypt(controlled_env):
    controlled_env.API_DECRYPT_PUBLIC_KEY = "not-a-valid-base64-der"
    controlled_env.API_DECRYPT_PRIVATE_KEY = "also-invalid"
    validate_security_settings()
    assert settings.API_DECRYPT_ENABLED is False


def test_disabled_stays_disabled_and_keys_untouched(controlled_env):
    """API_DECRYPT_ENABLED=False 时提前返回，不再触碰密钥配置。"""
    controlled_env.API_DECRYPT_ENABLED = False
    controlled_env.API_DECRYPT_PUBLIC_KEY = "garbage"
    validate_security_settings()
    assert settings.API_DECRYPT_ENABLED is False
    assert settings.API_DECRYPT_PUBLIC_KEY == "garbage"


# ---------- 正向：强密钥 + 有效 RSA 全通过 ----------


def test_prod_all_valid_keeps_decrypt_enabled(controlled_env, valid_rsa_pair):
    controlled_env.ENVIRONMENT = EnvironmentEnum.PROD
    public, private = valid_rsa_pair
    controlled_env.API_DECRYPT_PUBLIC_KEY = public
    controlled_env.API_DECRYPT_PRIVATE_KEY = private
    validate_security_settings()  # 不抛错
    assert settings.API_DECRYPT_ENABLED is True  # 密钥有效，保持启用不降级
