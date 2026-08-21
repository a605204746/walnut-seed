"""XSS 工具：HTML 标签剥离与脚本标记检测。"""

import re

# HTML 标签检测正则
RE_HTML_MARK = re.compile(r"(<[^<]*?>)|(<[<]*?[^<]*?>)", re.IGNORECASE)
# HTML 标签剥离正则
RE_STRIP_HTML = re.compile(r"<[^>]+>", re.IGNORECASE)


def clean_html_tag(content: str | None) -> str:
    """剥离全部 HTML 标签并去除首尾空白。"""
    if not content:
        return ""
    return RE_STRIP_HTML.sub("", content).strip()


def contains_html(content: str | None) -> bool:
    """检测是否包含 HTML/脚本标记。"""
    if not content:
        return False
    return bool(RE_HTML_MARK.search(content))
