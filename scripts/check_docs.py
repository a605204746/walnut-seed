"""Check documentation links and backend-specific filename/term consistency."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def markdown_files() -> list[Path]:
    return [ROOT / "README.md", ROOT / "README_EN.md", *DOCS.rglob("*.md")]


def check_links(errors: list[str]) -> None:
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip().split("#", 1)[0]
            if not target or re.match(r"^(?:https?|mailto:)", target):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"broken link: {path.relative_to(ROOT)} -> {target}")


def check_backend_docs(errors: list[str]) -> None:
    forbidden = {
        "python": ("docs/java",),
        "java": ("docs/python", "uv run main.py"),
    }
    for backend, terms in forbidden.items():
        for path in (DOCS / backend).glob("*.md"):
            text = path.read_text(encoding="utf-8")
            for term in terms:
                if term in text and term.startswith("docs/"):
                    errors.append(f"wrong backend path: {path.relative_to(ROOT)} contains {term}")


def check_expected_layout(errors: list[str]) -> None:
    expected = {
        "python": ["01-快速开始.md", "03-配置说明.md", "10-Docker部署.md", "11-生产上线清单.md"],
        "java": ["01-快速开始.md", "03-配置说明.md", "10-Docker部署.md", "11-生产上线清单.md"],
        "frontend": ["01-接口契约.md", "02-权限与动态路由.md"],
    }
    for directory, files in expected.items():
        for filename in files:
            if not (DOCS / directory / filename).exists():
                errors.append(f"missing expected doc: docs/{directory}/{filename}")


def main() -> int:
    errors: list[str] = []
    check_links(errors)
    check_backend_docs(errors)
    check_expected_layout(errors)
    if errors:
        print("文档检查失败：")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"文档检查通过：扫描 {len(markdown_files())} 个 Markdown 文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
