"""walnut-backend-python 全端点冒烟验收。

覆盖：认证全流程 + module_system/module_web/monitor 全部核心端点。
用法（walnut-backend-python 目录）：PYTHONPATH=. ENVIRONMENT=dev .venv/Scripts/python scripts/smoke_all.py
"""

import asyncio
import os

os.environ.setdefault("ENVIRONMENT", "dev")

import uvicorn  # noqa: E402

from app.common.enums import CacheNames  # noqa: E402
from app.core.redis_crud import full_key  # noqa: E402
from main import create_app  # noqa: E402

PORT = int(os.environ.get("SMOKE_PORT", "18090"))
BASE = f"http://127.0.0.1:{PORT}"
CLIENT_ID = "e5cd7e4891bf95d1d19206ce24a7b32e"

results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL"), name, detail if not ok else "")


async def main():
    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_config=None))
    task = asyncio.create_task(server.serve())
    await asyncio.sleep(6)

    import httpx
    import redis as redislib

    rr = redislib.from_url("redis://localhost:6379/0", decode_responses=True)

    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        H = {"clientid": CLIENT_ID}

        # ---------- 认证 ----------
        j = (await c.get("/auth/code", headers=H)).json()
        record("auth/code", j["code"] == 200 and j["data"].get("uuid"), str(j))
        ans = rr.get(full_key(CacheNames.CAPTCHA_CODE_KEY + j["data"]["uuid"]))

        r = await c.post("/auth/login", json={"clientId": CLIENT_ID, "grantType": "password", "username": "admin", "password": "WRONG1", "code": ans, "uuid": j["data"]["uuid"]}, headers=H)
        record("login 错误密码 → 10005", r.json()["code"] == 10005, str(r.json()))

        d = (await c.get("/auth/code", headers=H)).json()["data"]
        ans = rr.get(full_key(CacheNames.CAPTCHA_CODE_KEY + d["uuid"]))
        r = await c.post("/auth/login", json={"clientId": CLIENT_ID, "grantType": "password", "username": "admin", "password": "admin123", "code": ans, "uuid": d["uuid"]}, headers=H)
        body = r.json()
        tok = (body.get("data") or {}).get("access_token")
        record("login admin", body["code"] == 200 and tok, str(body)[:120])
        AH = {**H, "Authorization": f"Bearer {tok}"}

        async def get(path, **kw):
            return (await c.get(path, headers=AH, **kw)).json()

        async def req(method, path, **kw):
            return (await c.request(method, path, headers=AH, **kw)).json()

        # ---------- getInfo / 路由 ----------
        j = await get("/system/user/getInfo")
        record("user/getInfo", j["code"] == 200 and j["data"].get("user", {}).get("userName") == "admin" and "*:*:*" in j["data"].get("permissions", []), str(j)[:120])

        j = await get("/system/menu/getRouters")
        record("menu/getRouters", j["code"] == 200 and isinstance(j["data"], list) and len(j["data"]) > 0, str(j)[:80])

        # ---------- 部门 ----------
        j = await get("/system/dept/list")
        record("dept/list", j["code"] == 200 and isinstance(j["data"], list) and len(j["data"]) >= 10, str(j)[:80])
        j = await get("/system/dept/treeselect")
        record("dept/treeselect", j["code"] == 200 and j["data"][0].get("label"), str(j)[:80])
        j = await get("/system/dept/103")
        record("dept/103", j["code"] == 200 and j["data"].get("deptName") == "研发部门", str(j)[:100])

        # ---------- 岗位 ----------
        j = await get("/system/post/list?pageNum=1&pageSize=10")
        record("post/list", j["code"] == 200 and j["data"]["total"] == 4 and j["data"]["rows"][0].get("postCode"), str(j)[:80])

        # ---------- 字典 ----------
        j = await get("/system/dict/type/list?pageNum=1&pageSize=20")
        record("dict/type/list", j["code"] == 200 and j["data"]["total"] >= 10, str(j)[:60])
        j = await get("/system/dict/data/type/sys_user_sex")
        record("dict/data/type", j["code"] == 200 and isinstance(j["data"], list) and j["data"][0].get("dictLabel") in ("男", "女", "未知"), str(j)[:100])

        # ---------- 参数 ----------
        j = await get("/system/config/configKey/sys.user.initPassword")
        record("config/configKey", j["code"] == 200 and j["data"] == "123456", str(j))

        # ---------- 通知公告 ----------
        j = await get("/system/notice/list?pageNum=1&pageSize=10")
        record("notice/list", j["code"] == 200 and j["data"]["total"] == 2, str(j)[:80])

        # ---------- 客户端 ----------
        j = await get("/system/client/list?pageNum=1&pageSize=10")
        record("client/list", j["code"] == 200 and j["data"]["total"] == 2, str(j)[:80])

        # ---------- 社交 ----------
        j = await get("/system/social/list")
        record("social/list", j["code"] == 200, str(j)[:60])

        # ---------- 角色 ----------
        j = await get("/system/role/list?pageNum=1&pageSize=10")
        record("role/list", j["code"] == 200 and j["data"]["total"] == 3, str(j)[:80])
        j = await get("/system/role/deptTree/3")
        record("role/deptTree/3", j["code"] == 200 and "checkedKeys" in j["data"] and "depts" in j["data"], str(j)[:100])

        # ---------- 用户 ----------
        j = await get("/system/user/list?pageNum=1&pageSize=10")
        record("user/list", j["code"] == 200 and j["data"]["total"] >= 3, str(j)[:100])
        j = await get("/system/user/?")
        record("user/ (新增前置)", j["code"] == 200 and isinstance(j["data"].get("roles"), list), str(j)[:100])
        j = await get("/system/user/3")
        record("user/3", j["code"] == 200 and j["data"].get("user", {}).get("userName") == "test", str(j)[:100])
        j = await get("/system/user/authRole/3")
        record("user/authRole/3", j["code"] == 200 and j["data"].get("user"), str(j)[:100])
        j = await get("/system/user/deptTree")
        record("user/deptTree", j["code"] == 200 and isinstance(j["data"], list), str(j)[:60])
        j = await get("/system/user/list/dept/103")
        record("user/list/dept/103", j["code"] == 200 and isinstance(j["data"], list), str(j)[:60])

        # ---------- profile ----------
        j = await get("/system/user/profile")
        record("profile GET", j["code"] == 200 and j["data"].get("user", {}).get("userName") == "admin", str(j)[:100])

        # ---------- monitor ----------
        j = await get("/monitor/logininfor/list?pageNum=1&pageSize=10")
        record("logininfor/list", j["code"] == 200 and j["data"]["total"] >= 10, str(j)[:60])
        j = await get("/monitor/operlog/list?pageNum=1&pageSize=10")
        record("operlog/list", j["code"] == 200, str(j)[:60])

        # ---------- 数据权限验证（test 用户角色 test1=本部门及以下，有 list 权限但只能看到本部门数据） ----------
        d = (await c.get("/auth/code", headers=H)).json()["data"]
        ans = rr.get(full_key(CacheNames.CAPTCHA_CODE_KEY + d["uuid"]))
        r = await c.post("/auth/login", json={"clientId": CLIENT_ID, "grantType": "password", "username": "test", "password": "666666", "code": ans, "uuid": d["uuid"]}, headers=H)
        tok2 = (r.json().get("data") or {}).get("access_token")
        if tok2:
            r2 = await c.get("/system/user/list?pageNum=1&pageSize=10", headers={**H, "Authorization": f"Bearer {tok2}"})
            j2 = r2.json()
            rows = j2.get("data", {}).get("rows", [])
            names = [x.get("userName") for x in rows]
            record("test 用户数据权限过滤（只见本人）", j2["code"] == 200 and names == ["test"], str(j2)[:120])
            # menu/list 需 superadmin 角色，test 用户无此角色 → 403
            r3 = await c.get("/system/menu/list", headers={**H, "Authorization": f"Bearer {tok2}"})
            record("test 用户访问 menu/list → 403", r3.json()["code"] == 403, str(r3.json()))
        else:
            record("普通用户登录", False, str(r.json()))

        # ---------- 登出 ----------
        r = await c.post("/auth/logout", headers=AH)
        record("logout", r.json()["code"] == 200, str(r.json()))
        j = await get("/system/user/getInfo")
        record("登出后 getInfo → 401", j["code"] == 401, str(j)[:80])

    server.should_exit = True
    await task

    failed = [r for r in results if not r[1]]
    print(f"\n==== {len(results) - len(failed)}/{len(results)} passed ====")
    if failed:
        print("FAILED:", [f[0] for f in failed])
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
