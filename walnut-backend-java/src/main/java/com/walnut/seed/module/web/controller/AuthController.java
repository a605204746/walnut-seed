package com.walnut.seed.module.web.controller;

import cn.dev33.satoken.annotation.SaIgnore;
import cn.hutool.core.util.ObjectUtil;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.module.system.domain.model.LoginBody;
import com.walnut.seed.module.system.domain.model.RegisterBody;
import com.walnut.seed.common.core.json.utils.JsonUtils;
import com.walnut.seed.common.core.utils.DateUtils;
import com.walnut.seed.common.core.utils.MessageUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.core.utils.ValidatorUtils;
import com.walnut.seed.common.redis.ratelimiter.annotation.RateLimiter;
import com.walnut.seed.common.redis.ratelimiter.enums.LimitType;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.common.sse.dto.SseMessageDto;
import com.walnut.seed.common.sse.utils.SseMessageUtils;
import com.walnut.seed.module.system.domain.resp.SysClientResp;
import com.walnut.seed.module.system.service.SysClientService;
import com.walnut.seed.module.system.service.SysConfigService;
import com.walnut.seed.module.web.domain.resp.LoginResp;
import com.walnut.seed.module.web.service.IAuthStrategy;
import com.walnut.seed.module.web.service.SysLoginService;
import com.walnut.seed.module.web.service.SysRegisterService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.Date;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

/**
 * 认证
 *
 * @author deepin_sir
 */
@Slf4j
@SaIgnore
@RequiredArgsConstructor
@RestController
@RequestMapping("/auth")
public class AuthController {

    private final SysLoginService loginService;
    private final SysRegisterService registerService;
    private final SysConfigService configService;
    private final SysClientService clientService;
    private final ThreadPoolTaskExecutor walnutExecutor;


    /**
     * 登录方法
     * <p>
     * 接口加密为透明模式（与 Python 后端一致）：请求携带 {@code encrypt-key} 头时由
     * CryptoFilter 自动解密，未加密的明文请求同样放行（生产前端默认不开启加密）。
     *
     * @param body 登录信息
     * @return 结果
     */
    @PostMapping("/login")
    public ApiResponse<LoginResp> login(@RequestBody String body) {
        LoginBody loginBody = JsonUtils.parseObject(body, LoginBody.class);
        ValidatorUtils.validate(loginBody);
        // 授权类型和客户端id
        String clientId = loginBody.getClientId();
        String grantType = loginBody.getGrantType();
        SysClientResp client = clientService.queryByClientId(clientId);
        // 查询不到 client 或 client 内不包含 grantType
        if (ObjectUtil.isNull(client) || !StringUtils.contains(client.getGrantType(), grantType)) {
            log.info("客户端id: {} 认证类型：{} 异常!.", clientId, grantType);
            return ApiResponse.fail(MessageUtils.message("auth.grant.type.error"));
        } else if (!SystemConstants.NORMAL.equals(client.getStatus())) {
            return ApiResponse.fail(MessageUtils.message("auth.grant.type.blocked"));
        }
        // 登录
        LoginResp loginVo = IAuthStrategy.login(body, client, grantType);

        Long userId = LoginHelper.getUserId();
        CompletableFuture.delayedExecutor(5, TimeUnit.SECONDS, walnutExecutor).execute(() -> {
            SseMessageDto dto = new SseMessageDto();
            dto.setMessage(DateUtils.getTodayHour(new Date()) + "好，欢迎使用 WalnutSeed 管理后台");
            dto.setUserIds(List.of(userId));
            SseMessageUtils.publishMessage(dto);
        });
        return ApiResponse.ok(loginVo);
    }

    /**
     * 退出登录
     */
    @PostMapping("/logout")
    public ApiResponse<Void> logout() {
        loginService.logout();
        return ApiResponse.ok("退出成功");
    }

    /**
     * 用户注册（加密语义同登录：透明解密，明文放行）
     */
    @PostMapping("/register")
    public ApiResponse<Void> register(@Validated @RequestBody RegisterBody user) {
        if (!configService.selectRegisterEnabled()) {
            return ApiResponse.fail("当前系统没有开启注册功能！");
        }
        registerService.register(user);
        return ApiResponse.ok();
    }

    /**
     * 登录页面租户下拉框（兼容多租户前端）
     */
    @RateLimiter(time = 60, count = 20, limitType = LimitType.IP)
    @GetMapping("/tenant/list")
    public ApiResponse<TenantListVo> tenantList() {
        return ApiResponse.ok(TenantListVo.DISABLED_TENANT);
    }

    /**
     * 租户下拉列表
     *
     * @param tenantEnabled 租户开关
     */
    public record TenantListVo(boolean tenantEnabled){

        /**
         * 禁用租户，租户开关响应false（即关闭），让前端关闭租户功能
         */
        public static final TenantListVo DISABLED_TENANT = TenantListVo.of(false);

        public static TenantListVo of(boolean tenantEnabled){
            return new TenantListVo(tenantEnabled);
        }
    }

}
