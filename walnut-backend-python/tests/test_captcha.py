"""验证码生成回归测试。

锁定的行为：
- math 模式：算式与答案一致（重放计算验证）、减法结果非负、运算数范围受位数配置约束；
- 长度配置生效（number_length / char_length），非法小值有下限保护；
- 输出图片为可解码 PNG（base64）。
"""

import base64

import pytest

from app.api.v1.module_web.auth import captcha as captcha_mod
from app.api.v1.module_web.auth.captcha import generate_char, generate_math

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def stub_render(monkeypatch):
    """跳过耗时的图片渲染，只测算式/答案逻辑。"""
    monkeypatch.setattr(captcha_mod, "_render", lambda text: "stub-image")


def _decode_png(img_b64: str) -> bytes:
    raw = base64.b64decode(img_b64)
    assert raw.startswith(PNG_MAGIC)
    return raw


@pytest.mark.parametrize("number_length", [1, 2, 3])
def test_math_expression_matches_answer(stub_render, number_length):
    bound = 10**number_length
    seen_ops: set[str] = set()
    for _ in range(300):
        text, answer, _img = generate_math(number_length)
        assert text.endswith("=?")
        expr = text[:-2]
        if "+" in expr:
            left, right = expr.split("+")
            expected = int(left) + int(right)
            assert 0 <= expected <= 2 * (bound - 1)
            seen_ops.add("+")
        else:
            left, right = expr.split("-")
            expected = int(left) - int(right)
            assert expected >= 0  # 实现保证被减数 >= 减数
            seen_ops.add("-")
        assert 0 <= int(left) <= bound - 1
        assert 0 <= int(right) <= bound - 1
        assert int(answer) == expected  # 重放计算验证答案
    # 两种运算符都应出现（各 50% 概率，300 次不出现某一种的概率可忽略）
    assert seen_ops == {"+", "-"}


def test_math_zero_length_has_lower_bound(stub_render):
    # number_length=0 -> max(0,1)=1 位，运算数仍在 0-9
    for _ in range(50):
        text, answer, _img = generate_math(0)
        expr = text[:-2]
        left, right = expr.split("+") if "+" in expr else expr.split("-")
        assert 0 <= int(left) <= 9
        assert 0 <= int(right) <= 9
        assert answer.lstrip("-").isdigit()


def test_math_image_is_valid_png():
    for _ in range(3):
        _text, _answer, img = generate_math(2)
        _decode_png(img)


def test_char_captcha_contract():
    code, answer, img = generate_char(4)
    assert len(code) == 4
    assert code == answer  # char 模式展示文本即答案
    assert code.isalnum()
    _decode_png(img)


@pytest.mark.parametrize("char_length", [1, 6, 8])
def test_char_length_config(char_length):
    code, answer, _img = generate_char(char_length)
    assert len(code) == char_length
    assert code == answer


def test_char_length_lower_bound():
    code, _answer, _img = generate_char(0)  # 下限保护为 1 位
    assert len(code) == 1


def test_char_randomness(stub_render):
    # 多次生成不应全部相同（碰撞概率可忽略）
    codes = {generate_char(6)[0] for _ in range(20)}
    assert len(codes) > 1
