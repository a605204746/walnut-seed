package com.walnut.seed.module.system.controller.system;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.hutool.core.convert.Convert;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.module.system.domain.req.SysDeptReq;
import com.walnut.seed.module.system.domain.resp.SysDeptResp;
import com.walnut.seed.module.system.service.SysDeptService;
import com.walnut.seed.module.system.service.SysPostService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 部门信息
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/dept")
public class SysDeptController {

    private final SysDeptService deptService;
    private final SysPostService postService;

    /**
     * 获取部门列表
     */
    @SaCheckPermission("system:dept:list")
    @GetMapping("/list")
    public ApiResponse<List<SysDeptResp>> list(SysDeptReq req) {
        List<SysDeptResp> depts = deptService.selectDeptList(req);
        return ApiResponse.ok(depts);
    }

    /**
     * 查询部门列表（排除节点）
     *
     * @param deptId 部门ID
     */
    @SaCheckPermission("system:dept:list")
    @GetMapping("/list/exclude/{deptId}")
    public ApiResponse<List<SysDeptResp>> excludeChild(@PathVariable(value = "deptId", required = false) Long deptId) {
        List<SysDeptResp> depts = deptService.selectDeptList(new SysDeptReq());
        depts.removeIf(d -> d.getId().equals(deptId)
            || StringUtils.splitList(d.getAncestors()).contains(Convert.toStr(deptId)));
        return ApiResponse.ok(depts);
    }

    /**
     * 根据部门编号获取详细信息
     *
     * @param deptId 部门ID
     */
    @SaCheckPermission("system:dept:query")
    @GetMapping(value = "/{deptId}")
    public ApiResponse<SysDeptResp> get(@PathVariable Long deptId) {
        deptService.checkDeptDataScope(deptId);
        return ApiResponse.ok(deptService.selectDeptById(deptId));
    }

    /**
     * 新增部门
     */
    @SaCheckPermission("system:dept:add")
    @Log(title = "部门管理", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping
    public ApiResponse<Void> create(@Validated @RequestBody SysDeptReq req) {
        if (!deptService.checkDeptNameUnique(req)) {
            return ApiResponse.fail("新增部门'" + req.getDeptName() + "'失败，部门名称已存在");
        }
        return deptService.insertDept(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 修改部门
     */
    @SaCheckPermission("system:dept:edit")
    @Log(title = "部门管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping
    public ApiResponse<Void> update(@Validated @RequestBody SysDeptReq req) {
        Long deptId = req.getId();
        deptService.checkDeptDataScope(deptId);
        if (!deptService.checkDeptNameUnique(req)) {
            return ApiResponse.fail("修改部门'" + req.getDeptName() + "'失败，部门名称已存在");
        } else if (req.getParentId().equals(deptId)) {
            return ApiResponse.fail("修改部门'" + req.getDeptName() + "'失败，上级部门不能是自己");
        } else if (StringUtils.equals(SystemConstants.DISABLE, req.getStatus())) {
            if (deptService.selectNormalChildrenDeptById(deptId) > 0) {
                return ApiResponse.fail("该部门包含未停用的子部门!");
            } else if (deptService.checkDeptExistUser(deptId)) {
                return ApiResponse.fail("该部门下存在已分配用户，不能禁用!");
            }
        }
        return deptService.updateDept(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 删除部门
     *
     * @param deptId 部门ID
     */
    @SaCheckPermission("system:dept:remove")
    @Log(title = "部门管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{deptId}")
    public ApiResponse<Void> delete(@PathVariable Long deptId) {
        if (SystemConstants.DEFAULT_DEPT_ID.equals(deptId)) {
            return ApiResponse.warn("默认部门,不允许删除");
        }
        if (deptService.hasChildByDeptId(deptId)) {
            return ApiResponse.warn("存在下级部门,不允许删除");
        }
        if (deptService.checkDeptExistUser(deptId)) {
            return ApiResponse.warn("部门存在用户,不允许删除");
        }
        if (postService.countPostByDeptId(deptId) > 0) {
            return ApiResponse.warn("部门存在岗位,不允许删除");
        }
        deptService.checkDeptDataScope(deptId);
        return deptService.deleteDeptById(deptId) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 获取部门选择框列表
     *
     * @param deptIds 部门ID串
     */
    @SaCheckPermission("system:dept:query")
    @GetMapping("/optionselect")
    public ApiResponse<List<SysDeptResp>> optionselect(@RequestParam(required = false) Long[] deptIds) {
        return ApiResponse.ok(deptService.selectDeptByIds(deptIds == null ? null : List.of(deptIds)));
    }

}
