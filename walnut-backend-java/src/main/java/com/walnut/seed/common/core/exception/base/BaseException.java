package com.walnut.seed.common.core.exception.base;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;
import com.walnut.seed.common.core.utils.MessageUtils;
import com.walnut.seed.common.core.utils.StringUtils;

import java.io.Serial;

/**
 * 基础异常
 *
 * @author deepin_sir
 */
@Data
@EqualsAndHashCode(callSuper = true)
@NoArgsConstructor
@AllArgsConstructor
public class BaseException extends RuntimeException {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 所属模块
     */
    private String module;

    /**
     * 错误码（i18n 消息 key）
     */
    private String messageCode;

    /**
     * 错误码对应的参数
     */
    private Object[] args;

    /**
     * 错误消息
     */
    private String defaultMessage;

    public BaseException(String module, String messageCode, Object[] args) {
        this(module, messageCode, args, null);
    }

    public BaseException(String module, String defaultMessage) {
        this(module, null, null, defaultMessage);
    }

    public BaseException(String messageCode, Object[] args) {
        this(null, messageCode, args, null);
    }

    public BaseException(String defaultMessage) {
        this(null, null, null, defaultMessage);
    }

    @Override
    public String getMessage() {
        String message = null;
        if (!StringUtils.isEmpty(messageCode)) {
            message = MessageUtils.message(messageCode, args);
        }
        if (message == null) {
            message = defaultMessage;
        }
        return message;
    }

}
