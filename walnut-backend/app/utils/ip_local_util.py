"""IP 工具。

IP 归属地查询（ip2region）为可选能力：未提供离线库时返回占位结果，不影响主流程。
"""

import ipaddress

from app.utils.common_util import get_client_ip  # noqa: F401  (re-export，兼容引用)

UNKNOWN_IP = "XX XX"
LOCAL_ADDRESS = "内网IP"


def is_ipv4(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def is_ipv6(ip: str) -> bool:
    try:
        ipaddress.IPv6Address(ip)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def is_inner_ip(ip: str) -> bool:
    """判断是否内网/回环/链路本地地址。"""
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        return False


def get_real_address_by_ip(ip: str | None) -> str:
    """获取 IP 归属地。

    内网返回 ``内网IP``；无效返回 ``XX XX``；公网暂未接入离线库时返回 ``未知``。
    """
    if not ip:
        return UNKNOWN_IP
    if is_inner_ip(ip):
        return LOCAL_ADDRESS
    if not (is_ipv4(ip) or is_ipv6(ip)):
        return UNKNOWN_IP
    # 预留 ip2region 离线查询接入点；当前返回占位，避免启动期对外发起 HTTP 请求。
    return "未知"
