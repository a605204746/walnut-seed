"""雪花 ID 生成器回归测试。

锁定的整改行为：
- SNOWFLAKE_WORKER_ID 配置化：显式配置优先生效，非法值（<0 或 >1023）启动期即报错；
- 未配置时回退「本机 IP + 进程号」派生（结果仍落在 0-1023 合法域）；不同 IP / 同 IP 不同进程均可区分；
- 批量/并发生成 ID 唯一且严格单调递增；机器位正确内嵌于 ID。
"""

import threading

import pytest

from app.config.setting import settings
from app.utils.snowflake import IdGeneratorUtil, SnowflakeGenerator, _resolve_worker_id


def test_explicit_worker_id_in_constructor():
    assert SnowflakeGenerator(worker_id=42).worker_id == 42
    assert SnowflakeGenerator(worker_id=0).worker_id == 0
    assert SnowflakeGenerator(worker_id=1023).worker_id == 1023


@pytest.mark.parametrize("bad_worker_id", [-1, 1024, 99999])
def test_explicit_invalid_worker_id_rejected_in_constructor(bad_worker_id):
    """显式传入越界 worker_id 必须报错，禁止静默掩码回绕（回绕=伪装成另一实例，ID 冲突）。"""
    with pytest.raises(ValueError):
        SnowflakeGenerator(worker_id=bad_worker_id)


def test_resolve_worker_id_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "SNOWFLAKE_WORKER_ID", 77)
    assert _resolve_worker_id() == 77
    # 构造时未显式指定则取配置
    assert SnowflakeGenerator().worker_id == 77


@pytest.mark.parametrize("bad_worker_id", [-1, 1024, 99999])
def test_invalid_configured_worker_id_rejected(monkeypatch, bad_worker_id):
    monkeypatch.setattr(settings, "SNOWFLAKE_WORKER_ID", bad_worker_id)
    with pytest.raises(ValueError, match="SNOWFLAKE_WORKER_ID"):
        _resolve_worker_id()


@pytest.mark.parametrize("edge_worker_id", [0, 1023])
def test_boundary_configured_worker_id_accepted(monkeypatch, edge_worker_id):
    monkeypatch.setattr(settings, "SNOWFLAKE_WORKER_ID", edge_worker_id)
    assert _resolve_worker_id() == edge_worker_id


def test_fallback_worker_id_in_valid_range(monkeypatch):
    monkeypatch.setattr(settings, "SNOWFLAKE_WORKER_ID", None)
    worker_id = _resolve_worker_id()
    assert 0 <= worker_id <= 1023
    # 回退派生结果可被生成器直接使用
    assert SnowflakeGenerator().worker_id == worker_id


def test_fallback_differs_across_ips(monkeypatch):
    """不同机器/容器（不同 IP）派生出不同机器位。"""
    import app.utils.snowflake as snowflake_mod

    monkeypatch.setattr(settings, "SNOWFLAKE_WORKER_ID", None)
    monkeypatch.setattr(snowflake_mod, "_local_ip", lambda: "10.0.0.11")
    worker_a = _resolve_worker_id()
    monkeypatch.setattr(snowflake_mod, "_local_ip", lambda: "10.0.0.12")
    worker_b = _resolve_worker_id()
    assert worker_a != worker_b


def test_fallback_differs_across_processes_same_ip(monkeypatch):
    """同机多 worker 进程（同 IP 不同 PID）派生出不同机器位——主机名/纯 IP 方案覆盖不到的场景。"""
    import os

    import app.utils.snowflake as snowflake_mod

    monkeypatch.setattr(settings, "SNOWFLAKE_WORKER_ID", None)
    monkeypatch.setattr(snowflake_mod, "_local_ip", lambda: "192.168.1.100")
    monkeypatch.setattr(os, "getpid", lambda: 1000)
    worker_a = _resolve_worker_id()
    monkeypatch.setattr(os, "getpid", lambda: 1001)
    worker_b = _resolve_worker_id()
    assert worker_a != worker_b


def test_local_ip_probe_returns_string():
    """IP 探测在各环境下都必须返回非空字符串（离线时回退主机名解析/主机名）。"""
    from app.utils.snowflake import _local_ip

    identity = _local_ip()
    assert isinstance(identity, str) and identity


def test_batch_ids_unique_and_strictly_increasing():
    gen = SnowflakeGenerator(worker_id=3)
    ids = [gen.next_id() for _ in range(10000)]
    assert len(set(ids)) == len(ids)  # 无重复
    assert ids == sorted(ids)  # 单调递增（唯一性已保证严格递增）


def test_worker_id_embedded_in_id():
    gen = SnowflakeGenerator(worker_id=511)
    for _ in range(10):
        assert (gen.next_id() >> 12) & 1023 == 511


def test_concurrent_generation_no_duplicates():
    gen = SnowflakeGenerator(worker_id=9)
    results: list[int] = []
    lock = threading.Lock()

    def worker():
        local = [gen.next_id() for _ in range(2000)]
        with lock:
            results.extend(local)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 8000
    assert len(set(results)) == 8000


def test_id_generator_util():
    a = IdGeneratorUtil.next_long_id()
    b = IdGeneratorUtil.next_long_id()
    assert isinstance(a, int) and a > 0
    assert b > a
    assert IdGeneratorUtil.next_id().isdigit()  # 字符串形式可用
    assert IdGeneratorUtil.next_uuid() != IdGeneratorUtil.next_uuid()
    assert IdGeneratorUtil.next_id_with_prefix("ORD").startswith("ORD")
