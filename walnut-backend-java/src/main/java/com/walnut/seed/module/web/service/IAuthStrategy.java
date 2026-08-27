package com.walnut.seed.module.web.service;


import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.utils.SpringUtils;
import com.walnut.seed.module.system.domain.resp.SysClientResp;
import com.walnut.seed.module.web.domain.resp.LoginResp;

/**
 * 授权策略
 *
 * @author deepin_sir
 */
public interface IAuthStrategy {

    String BASE_NAME = "AuthStrategy";

    /**
     * 登录
     *
     * @param body      登录对象
     * @param client    授权管理视图对象
     * @param grantType 授权类型
     * @return 登录验证信息
     */
    static LoginResp login(String body, SysClientResp client, String grantType) {
        // 授权类型和客户端id
        String beanName = grantType + BASE_NAME;
        if (!SpringUtils.containsBean(beanName)) {
            throw new ServiceException("授权类型不正确!");
        }
        IAuthStrategy instance = SpringUtils.getBean(beanName);
        return instance.login(body, client);
    }

    /**
     * 登录
     *
     * @param body   登录对象
     * @param client 授权管理视图对象
     * @return 登录验证信息
     */
    LoginResp login(String body, SysClientResp client);

}
