package com.walnut.seed.module.web.exception;

import com.walnut.seed.common.core.exception.ErrorCode;
import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 认证模块错误码（号段 10000-19999）
 * <p>
 * 消息文案走 i18n（messages.properties），此处只存 key。
 * </p>
 *
 * @author deepin_sir
 */
@Getter
@AllArgsConstructor
public enum AuthErrorCode implements ErrorCode {

    /** 验证码已失效 */
    CAPTCHA_EXPIRED(10001, "user.jcaptcha.expire"),

    /** 验证码错误 */
    CAPTCHA_ERROR(10002, "user.jcaptcha.error"),

    /** 账号不存在 */
    USER_NOT_EXISTS(10003, "user.not.exists"),

    /** 账号已禁用 */
    USER_BLOCKED(10004, "user.blocked"),

    /** 密码输错 N 次（提醒） */
    USER_PASSWORD_RETRY_LIMIT_COUNT(10005, "user.password.retry.limit.count"),

    /** 密码输错超限，账户锁定 */
    USER_PASSWORD_RETRY_LIMIT_EXCEED(10006, "user.password.retry.limit.exceed"),

    /** 注册失败 */
    USER_REGISTER_FAILED(10007, "user.register.error"),

    /** 注册失败：账号已存在 */
    USER_REGISTER_EXISTS(10008, "user.register.save.error");

    private final int code;

    private final String key;
}
