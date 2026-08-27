package com.walnut.seed.module.system.controller.monitor;

import com.walnut.seed.common.core.constant.CacheNames;
import com.walnut.seed.common.core.domain.PageResult;

import cn.dev33.satoken.annotation.SaCheckPermission;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.excel.utils.ExcelUtil;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.module.system.domain.req.SysLogininforReq;
import com.walnut.seed.module.system.domain.resp.SysLogininforResp;
import com.walnut.seed.module.system.service.SysLogininforService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 系统访问记录
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/monitor/logininfor")
public class SysLogininforController {

    private final SysLogininforService logininforService;

    /**
     * 获取系统访问记录列表
     */
    @SaCheckPermission("monitor:logininfor:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysLogininforResp>> list(SysLogininforReq req) {
        return ApiResponse.ok(logininforService.selectPageLogininforList(req));
    }

    /**
     * 导出系统访问记录列表
     */
    @Log(title = "登录日志", businessType = BusinessType.EXPORT)
    @SaCheckPermission("monitor:logininfor:export")
    @PostMapping("/export")
    public void export(SysLogininforReq req, HttpServletResponse response) {
        List<SysLogininforResp> list = logininforService.selectLogininforList(req);
        ExcelUtil.exportExcel(list, "登录日志", SysLogininforResp.class, response);
    }

    /**
     * 批量删除登录日志
     * @param infoIds 日志ids
     */
    @SaCheckPermission("monitor:logininfor:remove")
    @Log(title = "登录日志", businessType = BusinessType.DELETE)
    @DeleteMapping("/{infoIds}")
    public ApiResponse<Void> delete(@PathVariable Long[] infoIds) {
        return logininforService.deleteLogininforByIds(infoIds) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 清理系统访问记录
     */
    @SaCheckPermission("monitor:logininfor:remove")
    @Log(title = "登录日志", businessType = BusinessType.CLEAN)
    @DeleteMapping("/clean")
    public ApiResponse<Void> clean() {
        RedisUtils.lock("lock:logininfor:clean", logininforService::cleanLogininfor);
        return ApiResponse.ok();
    }

    /**
     * 账户解锁
     *
     * @param userName 用户名
     */
    @SaCheckPermission("monitor:logininfor:unlock")
    @Log(title = "账户解锁", businessType = BusinessType.OTHER)
    @RepeatSubmit()
    @GetMapping("/unlock/{userName}")
    public ApiResponse<Void> unlock(@PathVariable("userName") String userName) {
        String loginName = CacheNames.PWD_ERR_CNT_KEY + userName;
        if (RedisUtils.hasKey(loginName)) {
            RedisUtils.deleteObject(loginName);
        }
        return ApiResponse.ok();
    }

}
