import os

# 先设置测试环境，再导入应用（必须在 import app 之前）
os.environ["ENVIRONMENT"] = "dev"
os.environ["DATABASE_TYPE"] = "mysql"
os.environ["DATABASE_NAME"] = "test_walnut_seed"
os.environ["REDIS_HOST"] = "localhost"
# 测试环境关闭启动自动迁移（无 MySQL 时 lifespan 静默跳过，不产生迁移噪音）
os.environ["DATABASE_AUTO_MIGRATE"] = "false"

from unittest.mock import patch  # noqa: E402

import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def make_request():
    """构造最小 Starlette Request（不起请求链路），供路由依赖/认证函数级测试直接调用。"""
    from starlette.requests import Request

    def factory(path="/test", method="POST", headers=None, query=b"", body=b"", client_addr="10.0.0.1"):
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query,
            "headers": [(k.lower().encode("utf-8"), v.encode("utf-8")) for k, v in (headers or {}).items()],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": (client_addr, 54321),
            "root_path": "",
        }
        return Request(scope, receive=receive)

    return factory


@pytest.fixture
def client(fake_redis):
    async def fake_redis_connect(app, status):
        if status:
            app.state.redis = fake_redis
            return fake_redis
        return None

    with patch("app.core.database.redis_connect", fake_redis_connect):
        from fastapi.testclient import TestClient

        from main import create_app

        app = create_app()
        with TestClient(app) as c:
            yield c
