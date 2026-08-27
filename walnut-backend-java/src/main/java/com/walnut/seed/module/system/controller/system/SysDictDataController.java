package com.walnut.seed.module.system.controller.system;
import com.walnut.seed.common.core.domain.PageResult;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.hutool.core.util.ObjectUtil;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.excel.utils.ExcelUtil;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.module.system.domain.req.SysDictDataReq;
import com.walnut.seed.module.system.domain.resp.SysDictDataResp;
import com.walnut.seed.module.system.service.SysDictDataService;
import com.walnut.seed.module.system.service.SysDictTypeService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
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
@RequestMapping("/system/dict/data")
public class SysDictDataController {

    private final SysDictDataService dictDataService;
    private final SysDictTypeService dictTypeService;

    /**
     * 查询字典数据列表
     */
    @SaCheckPermission("system:dict:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysDictDataResp>> list(SysDictDataReq req) {
        return ApiResponse.ok(dictDataService.selectPageDictDataList(req));
    }

    /**
     * 导出字典数据列表
     */
    @Log(title = "字典数据", businessType = BusinessType.EXPORT)
    @SaCheckPermission("system:dict:export")
    @PostMapping("/export")
    public void export(SysDictDataReq req, HttpServletResponse response) {
        List<SysDictDataResp> list = dictDataService.selectDictDataList(req);
        ExcelUtil.exportExcel(list, "字典数据", SysDictDataResp.class, response);
    }

    /**
     * 查询字典数据详细
     *
     * @param dictCode 字典code
     */
    @SaCheckPermission("system:dict:query")
    @GetMapping(value = "/{dictCode}")
    public ApiResponse<SysDictDataResp> get(@PathVariable Long dictCode) {
        return ApiResponse.ok(dictDataService.selectDictDataById(dictCode));
    }

    /**
     * 根据字典类型查询字典数据信息
     *
     * @param dictType 字典类型
     */
    @GetMapping(value = "/type/{dictType}")
    public ApiResponse<List<SysDictDataResp>> dictType(@PathVariable String dictType) {
        List<SysDictDataResp> data = dictTypeService.selectDictDataByType(dictType);
        if (ObjectUtil.isNull(data)) {
            data = new ArrayList<>();
        }
        return ApiResponse.ok(data);
    }

    /**
     * 新增字典数据
     */
    @SaCheckPermission("system:dict:add")
    @Log(title = "字典数据", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping
    public ApiResponse<Void> create(@Validated @RequestBody SysDictDataReq req) {
        if (!dictDataService.checkDictDataUnique(req)) {
            return ApiResponse.fail("新增字典数据'" + req.getDictValue() + "'失败，字典键值已存在");
        }
        dictDataService.insertDictData(req);
        return ApiResponse.ok();
    }

    /**
     * 修改保存字典数据
     */
    @SaCheckPermission("system:dict:edit")
    @Log(title = "字典数据", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping
    public ApiResponse<Void> update(@Validated @RequestBody SysDictDataReq req) {
        if (!dictDataService.checkDictDataUnique(req)) {
            return ApiResponse.fail("修改字典数据'" + req.getDictValue() + "'失败，字典键值已存在");
        }
        dictDataService.updateDictData(req);
        return ApiResponse.ok();
    }

    /**
     * 删除字典数据
     *
     * @param dictCodes 字典code串
     */
    @SaCheckPermission("system:dict:remove")
    @Log(title = "字典数据", businessType = BusinessType.DELETE)
    @DeleteMapping("/{dictCodes}")
    public ApiResponse<Void> delete(@PathVariable Long[] dictCodes) {
        dictDataService.deleteDictDataByIds(Arrays.asList(dictCodes));
        return ApiResponse.ok();
    }
}
