"""字符串工具。"""

SEPARATOR = ","
SLASH = "/"


def is_empty(value: str | None) -> bool:
    return value is None or len(value) == 0


def is_blank(value: str | None) -> bool:
    return value is None or len(value.strip()) == 0


def is_not_blank(value: str | None) -> bool:
    return not is_blank(value)


def blank_to_default(value: str | None, default: str) -> str:
    return default if value is None or not value.strip() else value


def str2list(value: str | None, sep: str = SEPARATOR, filter_blank: bool = True, trim: bool = True) -> list[str]:
    """字符串按分隔符转列表。"""
    if is_blank(value):
        return []
    parts = value.split(sep)  # type: ignore[union-attr]
    result = []
    for p in parts:
        item = p.strip() if trim else p
        if filter_blank and not item:
            continue
        result.append(item)
    return result


def str2set(value: str | None, sep: str = SEPARATOR) -> set[str]:
    return set(str2list(value, sep))


def join_comma(items) -> str:
    return SEPARATOR.join(str(i) for i in items)


def is_http(url: str | None) -> bool:
    return bool(url) and (url.startswith("http://") or url.startswith("https://"))  # type: ignore[union-attr]


def contains_any_ignore_case(value: str | None, *targets: str) -> bool:
    if not value:
        return False
    low = value.lower()
    return any(t and t.lower() in low for t in targets)


def start_with_any_ignore_case(value: str | None, *prefixes: str) -> bool:
    if not value:
        return False
    low = value.lower()
    return any(p and low.startswith(p.lower()) for p in prefixes)


def equals_ignore_case(a: str | None, b: str | None) -> bool:
    """忽略大小写比较（None 仅与 None 相等）。"""
    if a is None or b is None:
        return a is None and b is None
    return a.lower() == b.lower()
