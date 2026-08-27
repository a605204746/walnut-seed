package com.walnut.seed.module.system.controller.system;
import com.walnut.seed.common.core.domain.PageResult;

import cn.dev33.satoken.annotation.SaCheckPermission;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.core.validate.AddGroup;
import com.walnut.seed.common.core.validate.EditGroup;
import com.walnut.seed.common.excel.utils.ExcelUtil;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.module.system.domain.req.SysClientReq;
import com.walnut.seed.module.system.domain.resp.SysClientResp;
import com.walnut.seed.module.system.service.SysClientService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 客户端管理
 *
 * @author deepin_sir
 * @date 2023-06-18
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/client")
public class SysClientController {

    private final SysClientService sysClientService;

    /**
     * 查询客户端管理列表
     */
    @SaCheckPermission("system:client:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysClientResp>> list(SysClientReq req) {
        return ApiResponse.ok(sysClientService.queryPageList(req));
    }

    /**
     * 导出客户端管理列表
     */
    @SaCheckPermission("system:client:export")
    @Log(title = "客户端管理", businessType = BusinessType.EXPORT)
    @PostMapping("/export")
    public void export(SysClientReq req, HttpServletResponse response) {
        List<SysClientResp> list = sysClientService.queryList(req);
        ExcelUtil.exportExcel(list, "客户端管理", SysClientResp.class, response);
    }

    /**
     * 获取客户端管理详细信息
     *
     * @param id 主键
     */
    @SaCheckPermission("system:client:query")
    @GetMapping("/{id}")
    public ApiResponse<SysClientResp> get(@NotNull(message = "主键不能为空")
                                  @PathVariable Long id) {
        return ApiResponse.ok(sysClientService.queryById(id));
    }

    /**
     * 新增客户端管理
     */
    @SaCheckPermission("system:client:add")
    @Log(title = "客户端管理", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping()
    public ApiResponse<Void> create(@Validated(AddGroup.class) @RequestBody SysClientReq req) {
        if (!sysClientService.checkClickKeyUnique(req)) {
            return ApiResponse.fail("新增客户端'" + req.getClientKey() + "'失败，客户端key已存在");
        }
        return sysClientService.insertByBo(req) ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 修改客户端管理
     */
    @SaCheckPermission("system:client:edit")
    @Log(title = "客户端管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping()
    public ApiResponse<Void> update(@Validated(EditGroup.class) @RequestBody SysClientReq req) {
        if (!sysClientService.checkClickKeyUnique(req)) {
            return ApiResponse.fail("修改客户端'" + req.getClientKey() + "'失败，客户端key已存在");
        }
        return sysClientService.updateByBo(req) ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 状态修改
     */
    @SaCheckPermission("system:client:edit")
    @Log(title = "客户端管理", businessType = BusinessType.UPDATE)
    @PutMapping("/changeStatus")
    public ApiResponse<Void> changeStatus(@RequestBody SysClientReq req) {
        return sysClientService.updateClientStatus(req.getClientId(), req.getStatus()) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 删除客户端管理
     *
     * @param ids 主键串
     */
    @SaCheckPermission("system:client:remove")
    @Log(title = "客户端管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{ids}")
    public ApiResponse<Void> delete(@NotEmpty(message = "主键不能为空")
                          @PathVariable Long[] ids) {
        return sysClientService.deleteWithValidByIds(List.of(ids), true) ? ApiResponse.ok() : ApiResponse.fail();
    }
}
