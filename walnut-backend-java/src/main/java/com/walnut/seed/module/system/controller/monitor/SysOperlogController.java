package com.walnut.seed.module.system.controller.monitor;
import com.walnut.seed.common.core.domain.PageResult;

import cn.dev33.satoken.annotation.SaCheckPermission;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.excel.utils.ExcelUtil;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.module.system.domain.req.SysOperLogReq;
import com.walnut.seed.module.system.domain.resp.SysOperLogResp;
import com.walnut.seed.module.system.service.SysOperLogService;
import com.walnut.seed.common.redis.utils.RedisUtils;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 操作日志记录
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/monitor/operlog")
public class SysOperlogController {

    private final SysOperLogService operLogService;

    /**
     * 获取操作日志记录列表
     */
    @SaCheckPermission("monitor:operlog:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysOperLogResp>> list(SysOperLogReq req) {
        return ApiResponse.ok(operLogService.selectPageOperLogList(req));
    }

    /**
     * 导出操作日志记录列表
     */
    @Log(title = "操作日志", businessType = BusinessType.EXPORT)
    @SaCheckPermission("monitor:operlog:export")
    @PostMapping("/export")
    public void export(SysOperLogReq req, HttpServletResponse response) {
        List<SysOperLogResp> list = operLogService.selectOperLogList(req);
        ExcelUtil.exportExcel(list, "操作日志", SysOperLogResp.class, response);
    }

    /**
     * 批量删除操作日志记录
     * @param operIds 日志ids
     */
    @Log(title = "操作日志", businessType = BusinessType.DELETE)
    @SaCheckPermission("monitor:operlog:remove")
    @DeleteMapping("/{operIds}")
    public ApiResponse<Void> delete(@PathVariable Long[] operIds) {
        return operLogService.deleteOperLogByIds(operIds) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 清理操作日志记录
     */
    @Log(title = "操作日志", businessType = BusinessType.CLEAN)
    @SaCheckPermission("monitor:operlog:remove")
    @DeleteMapping("/clean")
    public ApiResponse<Void> clean() {
        RedisUtils.lock("lock:operlog:clean", () -> operLogService.cleanOperLog());
        return ApiResponse.ok();
    }
}
