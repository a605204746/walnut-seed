"""雪花 ID 生成器。

实现标准雪花算法：
1 位符号 + 41 位时间戳 + 10 位机器位 + 12 位序列号。

机器位（worker_id）优先取配置 ``SNOWFLAKE_WORKER_ID``（0-1023，多 worker 部署必须显式配置）；
未配置时回退为「本机出口 IP + 进程号」派生，并告警一次提示显式配置。
"""

import threading
import time
import uuid

# 起始时间戳（2020-01-01 00:00:00 UTC，毫秒）
_EPOCH = 1577836800000
_WORKER_ID_BITS = 10
_SEQUENCE_BITS = 12
_MAX_WORKER_ID = (1 << _WORKER_ID_BITS) - 1
_MAX_SEQUENCE = (1 << _SEQUENCE_BITS) - 1
_WORKER_ID_SHIFT = _SEQUENCE_BITS
_TIMESTAMP_SHIFT = _SEQUENCE_BITS + _WORKER_ID_BITS

# 回退派生是否已告警（仅提示一次）
_FALLBACK_WARNED = False


def _local_ip() -> str:
    """获取本机默认出口 IP；探测失败时回退主机名解析、再回退主机名本身。"""
    import socket

    try:
        # 对公网地址发起 UDP connect 仅是让内核选路，不实际发包，可安全离线使用
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("114.114.114.114", 53))
            return sock.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return socket.gethostname()


def _resolve_worker_id() -> int:
    """解析机器位：配置优先（校验 0-1023），未配置回退「IP + 进程号」派生并告警一次。

    派生思路：crc32(本机 IP) 区分不同机器/容器副本，叠加进程号区分
    同一台机器上的多个 worker 进程（它们共享同一 IP）。
    回退始终是尽力而为（IP 可能随 DHCP/容器重建变化），正式多实例部署仍应显式配置。
    """
    global _FALLBACK_WARNED
    from app.config.setting import settings

    configured = settings.SNOWFLAKE_WORKER_ID
    if configured is not None:
        if not 0 <= configured <= _MAX_WORKER_ID:
            raise ValueError(f"SNOWFLAKE_WORKER_ID 必须在 0-{_MAX_WORKER_ID} 范围内，当前值：{configured}")
        return configured
    if not _FALLBACK_WARNED:
        _FALLBACK_WARNED = True
        from app.core.logger import logger

        logger.warning("⚠️ SNOWFLAKE_WORKER_ID 未配置，雪花机器位回退为「本机 IP + 进程号」派生；多 worker/多副本部署必须显式配置且各实例互不相同")
    import os
    import zlib

    return (zlib.crc32(_local_ip().encode("utf-8")) + os.getpid()) & _MAX_WORKER_ID


class SnowflakeGenerator:
    """线程安全的雪花 ID 生成器。"""

    def __init__(self, worker_id: int | None = None) -> None:
        if worker_id is None:
            worker_id = _resolve_worker_id()
        elif not 0 <= worker_id <= _MAX_WORKER_ID:
            # 显式传入的机器位必须合法；静默掩码会让越界值回绕成另一个实例的机器位，制造 ID 冲突
            raise ValueError(f"worker_id 必须在 0-{_MAX_WORKER_ID} 范围内，实际为 {worker_id}")
        self.worker_id = worker_id
        self._sequence = 0
        self._last_timestamp = -1
        self._lock = threading.Lock()

    def _current_millis(self) -> int:
        return int(time.time() * 1000)

    def next_id(self) -> int:
        with self._lock:
            timestamp = self._current_millis()
            if timestamp < self._last_timestamp:
                # 时钟回拨：顺延到上次时间戳，避免重复
                timestamp = self._last_timestamp
            if timestamp == self._last_timestamp:
                self._sequence = (self._sequence + 1) & _MAX_SEQUENCE
                if self._sequence == 0:
                    while timestamp <= self._last_timestamp:
                        timestamp = self._current_millis()
            else:
                self._sequence = 0
            self._last_timestamp = timestamp
            return ((timestamp - _EPOCH) << _TIMESTAMP_SHIFT) | (self.worker_id << _WORKER_ID_SHIFT) | self._sequence


# 全局单例
_id_generator = SnowflakeGenerator()


class IdGeneratorUtil:
    """ID 工具。"""

    @staticmethod
    def next_long_id() -> int:
        return _id_generator.next_id()

    @staticmethod
    def next_id() -> str:
        return str(_id_generator.next_id())

    @staticmethod
    def next_uuid() -> str:
        """32 位无横线 UUID。"""
        return uuid.uuid4().hex

    @staticmethod
    def next_id_with_prefix(prefix: str) -> str:
        return f"{prefix}{_id_generator.next_id()}"

    @staticmethod
    def next_uuid_with_prefix(prefix: str) -> str:
        return f"{prefix}{uuid.uuid4().hex}"


def uuid4_str() -> str:
    return uuid.uuid4().hex
