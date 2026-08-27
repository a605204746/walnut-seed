package com.walnut.seed.common.core.exception;

import cn.hutool.core.text.StrFormatter;
import com.walnut.seed.common.core.exception.base.BaseException;
import com.walnut.seed.common.core.utils.MessageUtils;
import lombok.Getter;

import java.io.Serial;

/**
 * 业务异常（支持占位符 {} 和 i18n）
 *
 * @author deepin_sir
 */
@Getter
public class ServiceException extends BaseException {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 错误码
     */
    private Integer code;

    /**
     * 错误提示
     */
    private String message;

    /**
     * 错误明细，内部调试错误
     */
    private String detailMessage;

    public ServiceException() {
        super();
    }

    public ServiceException(String message) {
        super(message);
        this.message = message;
    }

    public ServiceException(String message, Integer code) {
        super(message);
        this.message = message;
        this.code = code;
    }

    public ServiceException(String message, Object... args) {
        super(StrFormatter.format(message, args));
        this.message = StrFormatter.format(message, args);
    }

    /**
     * 按业务错误码构造（消息按 i18n key 解析）
     */
    public ServiceException(ErrorCode errorCode, Object... args) {
        this(errorCode.getCode(), errorCode.getKey(), args);
    }

    /**
     * 按数字码 + i18n key 构造（key 需动态确定的场景，如不同登录方式的消息 key）
     */
    public ServiceException(int code, String messageKey, Object... args) {
        super(messageKey, args);
        String resolved = MessageUtils.message(messageKey, args);
        this.message = resolved != null ? resolved : messageKey;
        this.code = code;
    }

    @Override
    public String getMessage() {
        return message;
    }

    public ServiceException setMessage(String message) {
        this.message = message;
        return this;
    }

    public ServiceException setDetailMessage(String detailMessage) {
        this.detailMessage = detailMessage;
        return this;
    }
}
