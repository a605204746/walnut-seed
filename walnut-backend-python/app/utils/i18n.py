"""国际化消息工具。

资源文件位于 ``app/i18n/messages_<locale>.properties``，格式为 ``key=value``。
语言环境由 LocaleMiddleware 按请求头 ``Accept-Language``（``Content-Language`` 兜底）解析，
通过 ContextVar 传递，默认 ``zh_CN``。找不到翻译时返回消息键本身。
"""

from contextvars import ContextVar, Token
from pathlib import Path

from app.config.path_conf import I18N_DIR

# 当前请求的语言环境
_locale_var: ContextVar[str] = ContextVar("locale", default="zh_CN")

# 已加载的消息表缓存：locale -> {key: value}
_messages_cache: dict[str, dict[str, str]] = {}


def set_locale(locale: str) -> Token | None:
    """设置当前语言环境，返回重置令牌（请求结束时交由 reset_locale 清理）。"""
    if locale:
        return _locale_var.set(locale)
    return None


def reset_locale(token: Token | None) -> None:
    """按 set_locale 返回的令牌还原语言环境。"""
    if token is not None:
        _locale_var.reset(token)


def get_locale() -> str:
    return _locale_var.get()


def _load_properties(path: Path) -> dict[str, str]:
    """解析 .properties 资源文件（key=value，# 开头为注释）。"""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def _messages_for(locale: str) -> dict[str, str]:
    if locale not in _messages_cache:
        # 精确匹配 -> 语言匹配 -> 默认 zh_CN
        candidates = [locale, locale.split("_")[0], "zh_CN"]
        merged: dict[str, str] = {}
        for cand in reversed(candidates):
            merged.update(_load_properties(I18N_DIR / f"messages_{cand}.properties"))
        _messages_cache[locale] = merged
    return _messages_cache[locale]


class MessageUtils:
    """国际化工具。"""

    @staticmethod
    def message(code: str, *args) -> str:
        """按当前语言环境解析消息键；未命中时返回键本身。

        ``args`` 用于填充 ``{0}``/``{1}`` 占位符。
        """
        if not code:
            return ""
        template = _messages_for(get_locale()).get(code)
        if template is None:
            # 无翻译则返回 code 本身
            return code
        if args:
            try:
                return template.format(*args)
            except (IndexError, KeyError):
                return template
        return template
