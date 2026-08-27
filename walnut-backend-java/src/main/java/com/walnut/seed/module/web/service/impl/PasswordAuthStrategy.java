package com.walnut.seed.module.web.service.impl;

import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.module.web.exception.AuthErrorCode;

import com.walnut.seed.common.core.constant.CacheNames;

import cn.dev33.satoken.stp.StpUtil;
import cn.dev33.satoken.stp.parameter.SaLoginParameter;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import com.walnut.seed.common.core.constant.Constants;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.module.system.domain.model.LoginUser;
import com.walnut.seed.module.system.domain.model.PasswordLoginBody;
import com.walnut.seed.common.core.enums.LoginType;
import com.walnut.seed.common.core.utils.MessageUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.core.utils.ValidatorUtils;
import com.walnut.seed.common.core.json.utils.JsonUtils;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.common.web.config.properties.CaptchaProperties;
import com.walnut.seed.module.system.domain.entity.SysUser;
import com.walnut.seed.module.system.domain.resp.SysClientResp;
import com.walnut.seed.module.system.domain.resp.SysUserResp;
import com.walnut.seed.module.system.mapper.SysUserMapper;
import com.walnut.seed.module.web.domain.resp.LoginResp;
import com.walnut.seed.module.web.service.IAuthStrategy;
import com.walnut.seed.module.web.service.SysLoginService;
import org.springframework.stereotype.Service;

/**
 * 密码认证策略
 *
 * @author deepin_sir
 */
@Slf4j
@Service("password" + IAuthStrategy.BASE_NAME)
@RequiredArgsConstructor
public class PasswordAuthStrategy implements IAuthStrategy {

    private final CaptchaProperties captchaProperties;
    private final SysLoginService loginService;
    private final SysUserMapper userMapper;

    @Override
    public LoginResp login(String body, SysClientResp client) {
        PasswordLoginBody loginBody = JsonUtils.parseObject(body, PasswordLoginBody.class);
        ValidatorUtils.validate(loginBody);
        String username = loginBody.getUsername();
        String password = loginBody.getPassword();
        String code = loginBody.getCode();
        String uuid = loginBody.getUuid();

        boolean captchaEnabled = captchaProperties.getEnable();
        // 验证码开关
        if (captchaEnabled) {
            validateCaptcha(username, code, uuid);
        }

        SysUserResp user = loadUserByUsername(username);
        loginService.checkLogin(LoginType.PASSWORD, username, () -> !BCrypt.checkpw(password, user.getPassword()));
        // 此处可根据登录用户的数据不同 自行创建 loginUser
        LoginUser loginUser = loginService.buildLoginUser(user);

        loginUser.setClientKey(client.getClientKey());
        loginUser.setDeviceType(client.getDeviceType());
        SaLoginParameter model = new SaLoginParameter();
        model.setDeviceType(client.getDeviceType());
        // 自定义分配 不同用户体系 不同 token 授权时间 不设置默认走全局 yml 配置
        // 例如: 后台用户30分钟过期 app用户1天过期
        model.setTimeout(client.getTimeout());
        model.setActiveTimeout(client.getActiveTimeout());
        model.setExtra(LoginHelper.CLIENT_KEY, client.getClientId());
        // 生成token
        LoginHelper.login(loginUser, model);

        LoginResp loginVo = new LoginResp();
        loginVo.setAccessToken(StpUtil.getTokenValue());
        loginVo.setExpireIn(StpUtil.getTokenTimeout());
        loginVo.setClientId(client.getClientId());
        return loginVo;
    }

    /**
     * 校验验证码
     *
     * @param username 用户名
     * @param code     验证码
     * @param uuid     唯一标识
     */
    private void validateCaptcha(String username, String code, String uuid) {
        String verifyKey = CacheNames.CAPTCHA_CODE_KEY + StringUtils.blankToDefault(uuid, "");
        String captcha = RedisUtils.getCacheObject(verifyKey);
        RedisUtils.deleteObject(verifyKey);
        if (captcha == null) {
            loginService.recordLogininfor(username, Constants.LOGIN_FAIL, MessageUtils.message("user.jcaptcha.expire"));
            throw new ServiceException(AuthErrorCode.CAPTCHA_EXPIRED);
        }
        if (!StringUtils.equalsIgnoreCase(code, captcha)) {
            loginService.recordLogininfor(username, Constants.LOGIN_FAIL, MessageUtils.message("user.jcaptcha.error"));
            throw new ServiceException(AuthErrorCode.CAPTCHA_ERROR);
        }
    }

    private SysUserResp loadUserByUsername(String username) {
        SysUserResp user = userMapper.selectVoOne(new LambdaQueryWrapper<SysUser>().eq(SysUser::getUserName, username));
        if (ObjectUtil.isNull(user)) {
            log.info("登录用户：{} 不存在.", username);
            throw new ServiceException(AuthErrorCode.USER_NOT_EXISTS, username);
        } else if (SystemConstants.DISABLE.equals(user.getStatus())) {
            log.info("登录用户：{} 已被停用.", username);
            throw new ServiceException(AuthErrorCode.USER_BLOCKED, username);
        }
        return user;
    }

}
