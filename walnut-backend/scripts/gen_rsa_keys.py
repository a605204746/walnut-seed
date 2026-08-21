"""生成接口加解密 RSA 密钥对（两对，base64 DER）。

用法（walnut-backend 目录）：
  生成并打印两对密钥：  .venv/Scripts/python scripts/gen_rsa_keys.py
  自定义密钥位数：       .venv/Scripts/python scripts/gen_rsa_keys.py --bits 2048

输出格式与 app/core/encrypt.py 兼容：公钥 SubjectPublicKeyInfo / 私钥 PKCS8 的 DER Base64。

前后端配对说明（RuoYi 契约，请求与响应各一对，方向相反）：
  请求加密对：前端 VITE_GLOB_RSA_PUBLIC_KEY  加密请求  ↔ 后端 API_DECRYPT_PRIVATE_KEY 解密请求
  响应加密对：后端 API_DECRYPT_PUBLIC_KEY    加密响应  ↔ 前端 VITE_GLOB_RSA_PRIVATE_KEY 解密响应
即：生成两对密钥后，一对的公钥给前端（请求加密），该对私钥留后端；
另一对的公钥留后端（响应加密），该对私钥给前端。
"""

import argparse
import base64
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def gen_keypair(bits: int) -> tuple[str, str]:
    """生成 RSA 密钥对，返回 (公钥 base64 DER, 私钥 base64 DER)。"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(public_der).decode("ascii"), base64.b64encode(private_der).decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成接口加解密 RSA 密钥对（两对：请求加密对 + 响应加密对）")
    parser.add_argument("--bits", type=int, default=1024, help="密钥位数，默认 1024（jsencrypt 兼容上限）")
    args = parser.parse_args()

    if args.bits < 1024:
        print("警告：密钥位数低于 1024 不安全，建议使用 1024 或 2048", file=sys.stderr)

    req_public, req_private = gen_keypair(args.bits)
    resp_public, resp_private = gen_keypair(args.bits)

    print("===== 请求加密对（前端加密请求 → 后端解密请求） =====")
    print(f"前端 VITE_GLOB_RSA_PUBLIC_KEY={req_public}")
    print(f"后端 API_DECRYPT_PRIVATE_KEY={req_private}")
    print()
    print("===== 响应加密对（后端加密响应 → 前端解密响应） =====")
    print(f"后端 API_DECRYPT_PUBLIC_KEY={resp_public}")
    print(f"前端 VITE_GLOB_RSA_PRIVATE_KEY={resp_private}")
    print()
    print("说明：请求加密对与响应加密对必须使用不同的密钥对；")
    print("后端配置 API_DECRYPT_PUBLIC_KEY/API_DECRYPT_PRIVATE_KEY，前端配置对应 VITE_GLOB_RSA_*。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
