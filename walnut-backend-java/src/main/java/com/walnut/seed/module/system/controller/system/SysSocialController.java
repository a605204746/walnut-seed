package com.walnut.seed.module.system.controller.system;

import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.domain.resp.SysSocialResp;
import com.walnut.seed.module.system.service.SysSocialService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 社会化关系
 *
 * @author deepin_sir
 * @date 2023-06-16
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/social")
public class SysSocialController {

    private final SysSocialService socialUserService;

    /**
     * 查询社会化关系列表
     */
    @GetMapping("/list")
    public ApiResponse<List<SysSocialResp>> list() {
        return ApiResponse.ok(socialUserService.queryListByUserId(LoginHelper.getUserId()));
    }

}
