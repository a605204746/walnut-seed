"""通用工具函数。"""

import importlib
import uuid
from collections.abc import Callable
from typing import Any


def uuid4_str() -> str:
    """32 位无横线 UUID。"""
    return uuid.uuid4().hex


def import_module(dotted_path: str, desc: str = "模块") -> Any:
    """按 ``a.b.c.ClassName`` 动态导入类/对象。"""
    module_path, _, attr_name = dotted_path.rpartition(".")
    module = importlib.import_module(module_path)
    obj = getattr(module, attr_name, None)
    if obj is None:
        raise ImportError(f"无法在 {module_path} 中找到{desc} {attr_name}")
    return obj


def to_under_score_case(camel: str) -> str:
    """驼峰转下划线。"""
    if not camel:
        return camel
    result = []
    for i, ch in enumerate(camel):
        if ch.isupper():
            if i > 0 and not camel[i - 1] == "_":
                result.append("_")
            result.append(ch.lower())
        else:
            result.append(ch)
    return "".join(result)


def to_camel_case(snake: str) -> str:
    """下划线转驼峰。"""
    if not snake:
        return snake
    parts = snake.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def build_tree(
    items: list[Any],
    get_id: Callable[[Any], Any],
    get_parent_id: Callable[[Any], Any],
    set_children: Callable[[Any, list[Any]], None],
    root_parent_id: Any = 0,
) -> list[Any]:
    """构建树结构。"""
    children_map: dict[Any, list[Any]] = {}
    for item in items:
        children_map.setdefault(get_parent_id(item), []).append(item)
    roots = children_map.get(root_parent_id, [])
    for item in items:
        set_children(item, children_map.get(get_id(item), []))
    return roots


def get_client_ip(request: Any) -> str | None:
    """从请求中提取客户端 IP。

    仅当直连地址（对端地址）在 ``settings.TRUSTED_PROXY_IPS`` 白名单内时，
    才解析 X-Forwarded-For / X-Real-IP 等代理头；否则一律返回对端地址，
    防止未经认证的客户端通过伪造代理头篡改 IP（绕过限流/锁定等策略）。
    """
    from app.config.setting import settings

    client = getattr(request, "client", None)
    peer_ip = client.host if client else None
    if not settings.TRUSTED_PROXY_IPS or peer_ip not in settings.TRUSTED_PROXY_IPS:
        return peer_ip
    headers = getattr(request, "headers", {})
    for header in ("X-Forwarded-For", "X-Real-IP", "Proxy-Client-IP", "WL-Proxy-Client-IP"):
        value = headers.get(header)
        if value and value.lower() != "unknown":
            return value.split(",")[0].strip()
    return peer_ip
