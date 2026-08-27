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
import com.walnut.seed.module.system.domain.req.SysDictTypeReq;
import com.walnut.seed.module.system.domain.resp.SysDictTypeResp;
import com.walnut.seed.module.system.service.SysDictTypeService;
import com.walnut.seed.common.redis.utils.RedisUtils;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.List;

/**
 * 数据字典信息
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/dict/type")
public class SysDictTypeController {

    private final SysDictTypeService dictTypeService;

    /**
     * 查询字典类型列表
     */
    @SaCheckPermission("system:dict:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysDictTypeResp>> list(SysDictTypeReq req) {
        return ApiResponse.ok(dictTypeService.selectPageDictTypeList(req));
    }

    /**
     * 导出字典类型列表
     */
    @Log(title = "字典类型", businessType = BusinessType.EXPORT)
    @SaCheckPermission("system:dict:export")
    @PostMapping("/export")
    public void export(SysDictTypeReq req, HttpServletResponse response) {
        List<SysDictTypeResp> list = dictTypeService.selectDictTypeList(req);
        ExcelUtil.exportExcel(list, "字典类型", SysDictTypeResp.class, response);
    }

    /**
     * 查询字典类型详细
     *
     * @param dictId 字典ID
     */
    @SaCheckPermission("system:dict:query")
    @GetMapping(value = "/{dictId}")
    public ApiResponse<SysDictTypeResp> get(@PathVariable Long dictId) {
        return ApiResponse.ok(dictTypeService.selectDictTypeById(dictId));
    }

    /**
     * 新增字典类型
     */
    @SaCheckPermission("system:dict:add")
    @Log(title = "字典类型", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping
    public ApiResponse<Void> create(@Validated @RequestBody SysDictTypeReq req) {
        if (!dictTypeService.checkDictTypeUnique(req)) {
            return ApiResponse.fail("新增字典'" + req.getDictName() + "'失败，字典类型已存在");
        }
        dictTypeService.insertDictType(req);
        return ApiResponse.ok();
    }

    /**
     * 修改字典类型
     */
    @SaCheckPermission("system:dict:edit")
    @Log(title = "字典类型", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping
    public ApiResponse<Void> update(@Validated @RequestBody SysDictTypeReq req) {
        if (!dictTypeService.checkDictTypeUnique(req)) {
            return ApiResponse.fail("修改字典'" + req.getDictName() + "'失败，字典类型已存在");
        }
        dictTypeService.updateDictType(req);
        return ApiResponse.ok();
    }

    /**
     * 删除字典类型
     *
     * @param dictIds 字典ID串
     */
    @SaCheckPermission("system:dict:remove")
    @Log(title = "字典类型", businessType = BusinessType.DELETE)
    @DeleteMapping("/{dictIds}")
    public ApiResponse<Void> delete(@PathVariable Long[] dictIds) {
        dictTypeService.deleteDictTypeByIds(Arrays.asList(dictIds));
        return ApiResponse.ok();
    }

    /**
     * 刷新字典缓存
     */
    @SaCheckPermission("system:dict:remove")
    @Log(title = "字典类型", businessType = BusinessType.CLEAN)
    @DeleteMapping("/refreshCache")
    public ApiResponse<Void> refreshCache() {
        RedisUtils.lock("lock:dict:refreshCache", dictTypeService::resetDictCache);
        return ApiResponse.ok();
    }

    /**
     * 获取字典选择框列表
     */
    @GetMapping("/optionselect")
    public ApiResponse<List<SysDictTypeResp>> optionselect() {
        List<SysDictTypeResp> dictTypes = dictTypeService.selectDictTypeAll();
        return ApiResponse.ok(dictTypes);
    }
}
