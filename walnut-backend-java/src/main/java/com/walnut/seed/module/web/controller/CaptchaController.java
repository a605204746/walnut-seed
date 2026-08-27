package com.walnut.seed.module.web.controller;

import com.walnut.seed.common.core.constant.CacheNames;

import cn.dev33.satoken.annotation.SaIgnore;
import cn.hutool.captcha.generator.CodeGenerator;
import cn.hutool.captcha.generator.MathGenerator;
import cn.hutool.captcha.generator.RandomGenerator;
import cn.hutool.core.util.IdUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import com.walnut.seed.common.core.constant.Constants;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.core.utils.SpringUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.redis.ratelimiter.annotation.RateLimiter;
import com.walnut.seed.common.redis.ratelimiter.enums.LimitType;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.common.web.core.WaveAndCircleCaptcha;
import com.walnut.seed.common.web.config.properties.CaptchaProperties;
import com.walnut.seed.module.web.domain.resp.CaptchaResp;
import org.springframework.expression.Expression;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.awt.*;
import java.time.Duration;

/**
 * 验证码操作处理
 *
 * @author deepin_sir
 */
@SaIgnore
@Slf4j
@RequiredArgsConstructor
@RestController
public class CaptchaController {

    private final CaptchaProperties captchaProperties;

    /**
     * 生成验证码
     */
    @GetMapping("/auth/code")
    public ApiResponse<CaptchaResp> getCode() {
        boolean captchaEnabled = captchaProperties.getEnable();
        if (!captchaEnabled) {
            CaptchaResp captchaVo = new CaptchaResp();
            captchaVo.setCaptchaEnabled(false);
            return ApiResponse.ok(captchaVo);
        }
        return ApiResponse.ok(SpringUtils.getAopProxy(this).getCodeImpl());
    }

    /**
     * 生成验证码
     * 独立方法避免验证码关闭之后仍然走限流
     */
    @RateLimiter(time = 60, count = 10, limitType = LimitType.IP)
    public CaptchaResp getCodeImpl() {
        String uuid = IdUtil.simpleUUID();
        String verifyKey = CacheNames.CAPTCHA_CODE_KEY + uuid;
        String captchaType = captchaProperties.getType();
        CodeGenerator codeGenerator;
        if ("math".equals(captchaType)) {
            codeGenerator = new MathGenerator(captchaProperties.getNumberLength(), false);
        } else {
            codeGenerator = new RandomGenerator(captchaProperties.getCharLength());
        }
        WaveAndCircleCaptcha captcha = new WaveAndCircleCaptcha(160, 60);
        captcha.setFont(new Font("Arial", Font.BOLD, 45));
        captcha.setGenerator(codeGenerator);
        captcha.createCode();
        String code = captcha.getCode();
        if ("math".equals(captchaType)) {
            ExpressionParser parser = new SpelExpressionParser();
            Expression exp = parser.parseExpression(StringUtils.remove(code, "="));
            code = exp.getValue(String.class);
        }
        RedisUtils.setCacheObject(verifyKey, code, Duration.ofMinutes(Constants.CAPTCHA_EXPIRATION));
        CaptchaResp captchaVo = new CaptchaResp();
        captchaVo.setUuid(uuid);
        captchaVo.setImg(captcha.getImageBase64());
        return captchaVo;
    }

}
