package com.walnut.seed.module.web.service;

import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.module.web.exception.AuthErrorCode;

import com.walnut.seed.common.core.constant.CacheNames;

import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.constant.Constants;
import com.walnut.seed.module.system.domain.model.RegisterBody;
import com.walnut.seed.common.core.enums.UserType;
import com.walnut.seed.common.core.utils.MessageUtils;
import com.walnut.seed.common.core.utils.ServletUtils;
import com.walnut.seed.common.core.utils.SpringUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.log.event.LogininforEvent;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.common.web.config.properties.CaptchaProperties;
import com.walnut.seed.module.system.domain.entity.SysUser;
import com.walnut.seed.module.system.domain.req.SysUserReq;
import com.walnut.seed.module.system.mapper.SysUserMapper;
import com.walnut.seed.module.system.service.SysUserService;
import org.springframework.stereotype.Service;

/**
 * 注册校验方法
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysRegisterService {

    private final SysUserService userService;
    private final SysUserMapper userMapper;
    private final CaptchaProperties captchaProperties;

    /**
     * 注册
     */
    public void register(RegisterBody registerBody) {
        String username = registerBody.getUsername();
        String password = registerBody.getPassword();
        // 校验用户类型是否存在
        String userType = UserType.getUserType(registerBody.getUserType()).getUserType();

        boolean captchaEnabled = captchaProperties.getEnable();
        // 验证码开关
        if (captchaEnabled) {
            validateCaptcha(username, registerBody.getCode(), registerBody.getUuid());
        }
        SysUserReq sysUser = new SysUserReq();
        sysUser.setUserName(username);
        sysUser.setNickName(username);
        sysUser.setPassword(BCrypt.hashpw(password));
        sysUser.setUserType(userType);

        boolean exist = userMapper.exists(new LambdaQueryWrapper<SysUser>().eq(SysUser::getUserName, sysUser.getUserName()));
        if (exist) {
            throw new ServiceException(AuthErrorCode.USER_REGISTER_EXISTS, username);
        }
        boolean regFlag = userService.registerUser(sysUser);
        if (!regFlag) {
            throw new ServiceException(AuthErrorCode.USER_REGISTER_FAILED);
        }
        recordLogininfor(username, Constants.REGISTER, MessageUtils.message("user.register.success"));
    }

    /**
     * 校验验证码
     *
     * @param username 用户名
     * @param code     验证码
     * @param uuid     唯一标识
     */
    public void validateCaptcha(String username, String code, String uuid) {
        String verifyKey = CacheNames.CAPTCHA_CODE_KEY + StringUtils.blankToDefault(uuid, "");
        String captcha = RedisUtils.getCacheObject(verifyKey);
        RedisUtils.deleteObject(verifyKey);
        if (captcha == null) {
            recordLogininfor(username, Constants.LOGIN_FAIL, MessageUtils.message("user.jcaptcha.expire"));
            throw new ServiceException(AuthErrorCode.CAPTCHA_EXPIRED);
        }
        if (!StringUtils.equalsIgnoreCase(code, captcha)) {
            recordLogininfor(username, Constants.LOGIN_FAIL, MessageUtils.message("user.jcaptcha.error"));
            throw new ServiceException(AuthErrorCode.CAPTCHA_ERROR);
        }
    }

    /**
     * 记录登录信息
     *
     * @param username 用户名
     * @param status   状态
     * @param message  消息内容
     * @return
     */
    private void recordLogininfor(String username, String status, String message) {
        LogininforEvent logininforEvent = new LogininforEvent();
        logininforEvent.setUsername(username);
        logininforEvent.setStatus(status);
        logininforEvent.setMessage(message);
        logininforEvent.setRequest(ServletUtils.getRequest());
        SpringUtils.context().publishEvent(logininforEvent);
    }

}
