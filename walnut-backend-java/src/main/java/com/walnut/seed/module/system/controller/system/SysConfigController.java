package com.walnut.seed.module.system.controller.system;
import com.walnut.seed.common.core.domain.PageResult;

import cn.dev33.satoken.annotation.SaCheckPermission;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.excel.utils.ExcelUtil;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.module.system.domain.req.SysConfigReq;
import com.walnut.seed.module.system.domain.resp.SysConfigResp;
import com.walnut.seed.module.system.service.SysConfigService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.List;

/**
 * 参数配置 信息操作处理
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/config")
public class SysConfigController {

    private final SysConfigService configService;

    /**
     * 获取参数配置列表
     */
    @SaCheckPermission("system:config:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysConfigResp>> list(SysConfigReq req) {
        return ApiResponse.ok(configService.selectPageConfigList(req));
    }

    /**
     * 导出参数配置列表
     */
    @Log(title = "参数管理", businessType = BusinessType.EXPORT)
    @SaCheckPermission("system:config:export")
    @PostMapping("/export")
    public void export(SysConfigReq req, HttpServletResponse response) {
        List<SysConfigResp> list = configService.selectConfigList(req);
        ExcelUtil.exportExcel(list, "参数数据", SysConfigResp.class, response);
    }

    /**
     * 根据参数编号获取详细信息
     *
     * @param configId 参数ID
     */
    @SaCheckPermission("system:config:query")
    @GetMapping(value = "/{configId}")
    public ApiResponse<SysConfigResp> get(@PathVariable Long configId) {
        return ApiResponse.ok(configService.selectConfigById(configId));
    }

    /**
     * 根据参数键名查询参数值
     *
     * @param configKey 参数Key
     */
    @GetMapping(value = "/configKey/{configKey}")
    public ApiResponse<String> getConfigKey(@PathVariable String configKey) {
        return ApiResponse.ok("操作成功", configService.selectConfigByKey(configKey));
    }

    /**
     * 新增参数配置
     */
    @SaCheckPermission("system:config:add")
    @Log(title = "参数管理", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping
    public ApiResponse<Void> create(@Validated @RequestBody SysConfigReq req) {
        if (!configService.checkConfigKeyUnique(req)) {
            return ApiResponse.fail("新增参数'" + req.getConfigName() + "'失败，参数键名已存在");
        }
        configService.insertConfig(req);
        return ApiResponse.ok();
    }

    /**
     * 修改参数配置
     */
    @SaCheckPermission("system:config:edit")
    @Log(title = "参数管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping
    public ApiResponse<Void> update(@Validated @RequestBody SysConfigReq req) {
        if (!configService.checkConfigKeyUnique(req)) {
            return ApiResponse.fail("修改参数'" + req.getConfigName() + "'失败，参数键名已存在");
        }
        configService.updateConfig(req);
        return ApiResponse.ok();
    }

    /**
     * 根据参数键名修改参数配置
     */
    @SaCheckPermission("system:config:edit")
    @Log(title = "参数管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping("/updateByKey")
    public ApiResponse<Void> updateByKey(@RequestBody SysConfigReq req) {
        configService.updateConfig(req);
        return ApiResponse.ok();
    }

    /**
     * 删除参数配置
     *
     * @param configIds 参数ID串
     */
    @SaCheckPermission("system:config:remove")
    @Log(title = "参数管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{configIds}")
    public ApiResponse<Void> delete(@PathVariable Long[] configIds) {
        configService.deleteConfigByIds(Arrays.asList(configIds));
        return ApiResponse.ok();
    }

    /**
     * 刷新参数缓存
     */
    @SaCheckPermission("system:config:remove")
    @Log(title = "参数管理", businessType = BusinessType.CLEAN)
    @DeleteMapping("/refreshCache")
    public ApiResponse<Void> refreshCache() {
        configService.resetConfigCache();
        return ApiResponse.ok();
    }
}
