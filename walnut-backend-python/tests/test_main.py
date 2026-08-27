"""核心架构冒烟测试：应用可启动、健康检查可用、符合统一响应信封 {code, msg, data} 契约。"""


def test_create_app():
    from fastapi import FastAPI

    from main import create_app

    app = create_app()
    assert isinstance(app, FastAPI)


def test_health_check_envelope(client):
    resp = client.get("/common/health/check")
    assert resp.status_code == 200
    body = resp.json()
    # 统一响应信封 {code, msg, data} 契约
    assert set(body.keys()) == {"code", "msg", "data"}
    assert body["code"] == 200
    assert body["msg"] == "系统健康"
    assert body["data"]["status"] == 1


def test_health_live(client):
    resp = client.get("/common/health/live")
    assert resp.status_code == 200
    assert resp.json()["code"] == 200


def test_not_found_returns_envelope(client):
    resp = client.get("/no-such-route")
    body = resp.json()
    assert body.get("code") == 404


def test_response_classes_contract():
    from app.common.response import ApiResponse, PageResult

    assert ApiResponse.SUCCESS == 200
    assert ApiResponse.FAIL == 500
    assert ApiResponse.WARN == 601
    page = PageResult(rows=[1, 2, 3], total=3)
    assert page.model_dump() == {"rows": [1, 2, 3], "total": 3}


def test_bigint_serialized_as_string():
    from app.common.response import jsonable_response_content

    # 超出 JS 安全整数范围的大整数应转为字符串
    result = jsonable_response_content({"id": 12345678901234567890, "small": 1})
    assert result["id"] == "12345678901234567890"
    assert result["small"] == 1
