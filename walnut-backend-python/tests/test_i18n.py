"""i18n 消息工具回归测试。

锁定的行为：
- ContextVar locale：set_locale 切换语言、reset_locale 还原 zh_CN 默认；
- 资源文件中真实键的中英文案都能取到；
- 未知 locale 回退 zh_CN；未知键原样返回键本身；
- 位置参数占位符 {0}/{1} 格式化。

注意：locale 存于 ContextVar，测试必须成对 set/reset，避免污染其他用例。
"""

from contextlib import contextmanager

from app.utils.i18n import MessageUtils, get_locale, reset_locale, set_locale


@contextmanager
def use_locale(locale: str):
    token = set_locale(locale)
    try:
        yield
    finally:
        reset_locale(token)


def test_default_locale_is_zh_cn():
    assert get_locale() == "zh_CN"


def test_zh_cn_message_from_properties():
    assert MessageUtils.message("user.password.not.match") == "用户不存在/密码错误"
    assert MessageUtils.message("repeat.submit.message") == "不允许重复提交，请稍候再试"


def test_en_us_message_from_properties():
    with use_locale("en_US"):
        assert MessageUtils.message("user.password.not.match") == "User does not exist or password is incorrect"
        assert MessageUtils.message("repeat.submit.message") == "Repeat submit is not allowed, please try again later"


def test_reset_locale_restores_default():
    token = set_locale("en_US")
    try:
        assert MessageUtils.message("rate.limiter.message") == "Visit too frequently, please try again later"
    finally:
        reset_locale(token)
    assert get_locale() == "zh_CN"
    assert MessageUtils.message("rate.limiter.message") == "访问过于频繁，请稍候再试"


def test_unknown_locale_falls_back_to_zh_cn():
    with use_locale("fr_FR"):
        assert MessageUtils.message("user.login.success") == "登录成功"


def test_language_only_locale_falls_back_to_default():
    # 无独立 messages_en.properties：语言前缀匹配落空后回退 zh_CN
    with use_locale("en"):
        assert MessageUtils.message("user.login.success") == "登录成功"


def test_unknown_key_returns_key_itself():
    assert MessageUtils.message("no.such.key.exists") == "no.such.key.exists"


def test_empty_code_returns_empty_string():
    assert MessageUtils.message("") == ""


def test_positional_args_formatted_zh():
    assert MessageUtils.message("user.password.retry.limit.exceed", 3, 10) == "密码输入错误3次，帐户锁定10分钟"


def test_positional_args_formatted_en():
    with use_locale("en_US"):
        assert MessageUtils.message("user.password.retry.limit.exceed", 3, 10) == "Password entered incorrectly 3 times, account locked for 10 minutes"


def test_set_empty_locale_is_noop():
    before = get_locale()
    assert set_locale("") is None
    assert get_locale() == before
