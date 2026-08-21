"""生成 JWT 签名密钥（SECRET_KEY）。

用法（walnut-backend 目录）：
  打印一个新密钥：        .venv/Scripts/python scripts/gen_secret_key.py
  写入指定 env 文件：     .venv/Scripts/python scripts/gen_secret_key.py --write env/.env.dev
  自定义密钥长度（字节）：.venv/Scripts/python scripts/gen_secret_key.py --bytes 64

--write 会替换文件中已有的 ``SECRET_KEY=`` 行，不存在则追加。
HS256 建议密钥 ≥32 字节（pyjwt 对更短的密钥会发出 InsecureKeyLengthWarning）。
"""

import argparse
import secrets
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 JWT 签名密钥（SECRET_KEY）")
    parser.add_argument("--bytes", type=int, default=32, help="密钥字节数，默认 32（HS256 建议 ≥32）")
    parser.add_argument("--write", type=Path, default=None, help="将密钥写入指定 env 文件（替换 SECRET_KEY= 行）")
    args = parser.parse_args()

    if args.bytes < 32:
        print("警告：HS256 建议密钥长度 ≥32 字节，过短会触发 InsecureKeyLengthWarning", file=sys.stderr)

    key = secrets.token_hex(args.bytes)

    if args.write is None:
        print(key)
        return 0

    path = args.write
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith("SECRET_KEY="):
            lines[i] = f"SECRET_KEY={key}"
            replaced = True
    if not replaced:
        lines.append(f"SECRET_KEY={key}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已{'替换' if replaced else '追加'} {path} 的 SECRET_KEY（{args.bytes * 2} 位 hex）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
