package com.walnut.seed.module.web.domain.resp;

import lombok.Data;

/**
 * 验证码信息
 *
 * @author deepin_sir
 */
@Data
public class CaptchaResp {

    /**
     * 是否开启验证码
     */
    private Boolean captchaEnabled = true;

    private String uuid;

    /**
     * 验证码图片
     */
    private String img;

}
