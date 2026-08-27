package com.walnut.seed.module.system.controller.system;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.hutool.core.lang.tree.Tree;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.core.domain.PageResult;
import com.walnut.seed.common.excel.utils.ExcelUtil;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.module.system.domain.entity.SysUserRole;
import com.walnut.seed.module.system.domain.req.SysDeptReq;
import com.walnut.seed.module.system.domain.req.SysRoleReq;
import com.walnut.seed.module.system.domain.req.SysUserReq;
import com.walnut.seed.module.system.domain.resp.SysRoleResp;
import com.walnut.seed.module.system.domain.resp.SysUserResp;
import com.walnut.seed.module.system.service.SysDeptService;
import com.walnut.seed.module.system.service.SysRoleService;
import com.walnut.seed.module.system.service.SysUserService;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 角色信息
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/role")
public class SysRoleController {

    private final SysRoleService roleService;
    private final SysUserService userService;
    private final SysDeptService deptService;

    /**
     * 获取角色信息列表
     */
    @SaCheckPermission("system:role:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysRoleResp>> list(SysRoleReq req) {
        return ApiResponse.ok(roleService.selectPageRoleList(req));
    }

    /**
     * 导出角色信息列表
     */
    @Log(title = "角色管理", businessType = BusinessType.EXPORT)
    @SaCheckPermission("system:role:export")
    @PostMapping("/export")
    public void export(SysRoleReq req, HttpServletResponse response) {
        List<SysRoleResp> list = roleService.selectRoleList(req);
        ExcelUtil.exportExcel(list, "角色数据", SysRoleResp.class, response);
    }

    /**
     * 根据角色编号获取详细信息
     *
     * @param roleId 角色ID
     */
    @SaCheckPermission("system:role:query")
    @GetMapping(value = "/{roleId}")
    public ApiResponse<SysRoleResp> get(@PathVariable Long roleId) {
        roleService.checkRoleDataScope(roleId);
        return ApiResponse.ok(roleService.selectRoleById(roleId));
    }

    /**
     * 新增角色
     */
    @SaCheckPermission("system:role:add")
    @Log(title = "角色管理", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping
    public ApiResponse<Void> create(@Validated @RequestBody SysRoleReq req) {
        roleService.checkRoleAllowed(req);
        if (!roleService.checkRoleNameUnique(req)) {
            return ApiResponse.fail("新增角色'" + req.getRoleName() + "'失败，角色名称已存在");
        } else if (!roleService.checkRoleKeyUnique(req)) {
            return ApiResponse.fail("新增角色'" + req.getRoleName() + "'失败，角色权限已存在");
        }
        return roleService.insertRole(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();

    }

    /**
     * 修改保存角色
     */
    @SaCheckPermission("system:role:edit")
    @Log(title = "角色管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping
    public ApiResponse<Void> update(@Validated @RequestBody SysRoleReq req) {
        roleService.checkRoleAllowed(req);
        roleService.checkRoleDataScope(req.getId());
        if (!roleService.checkRoleNameUnique(req)) {
            return ApiResponse.fail("修改角色'" + req.getRoleName() + "'失败，角色名称已存在");
        } else if (!roleService.checkRoleKeyUnique(req)) {
            return ApiResponse.fail("修改角色'" + req.getRoleName() + "'失败，角色权限已存在");
        }

        if (roleService.updateRole(req) > 0) {
            roleService.cleanOnlineUserByRole(req.getId());
            return ApiResponse.ok();
        }
        return ApiResponse.fail("修改角色'" + req.getRoleName() + "'失败，请联系管理员");
    }

    /**
     * 修改保存数据权限
     */
    @SaCheckPermission("system:role:edit")
    @Log(title = "角色管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping("/dataScope")
    public ApiResponse<Void> dataScope(@RequestBody SysRoleReq req) {
        roleService.checkRoleAllowed(req);
        roleService.checkRoleDataScope(req.getId());
        return roleService.authDataScope(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 状态修改
     */
    @SaCheckPermission("system:role:edit")
    @Log(title = "角色管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping("/changeStatus")
    public ApiResponse<Void> changeStatus(@RequestBody SysRoleReq req) {
        roleService.checkRoleAllowed(req);
        roleService.checkRoleDataScope(req.getId());
        return roleService.updateRoleStatus(req.getId(), req.getStatus()) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 删除角色
     *
     * @param roleIds 角色ID串
     */
    @SaCheckPermission("system:role:remove")
    @Log(title = "角色管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{roleIds}")
    public ApiResponse<Void> delete(@PathVariable Long[] roleIds) {
        return roleService.deleteRoleByIds(List.of(roleIds)) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 获取角色选择框列表
     *
     * @param roleIds 角色ID串
     */
    @SaCheckPermission("system:role:query")
    @GetMapping("/optionselect")
    public ApiResponse<List<SysRoleResp>> optionselect(@RequestParam(required = false) Long[] roleIds) {
        return ApiResponse.ok(roleService.selectRoleByIds(roleIds == null ? null : List.of(roleIds)));
    }

    /**
     * 查询已分配用户角色列表
     */
    @SaCheckPermission("system:role:list")
    @GetMapping("/authUser/allocatedList")
    public ApiResponse<PageResult<SysUserResp>> allocatedList(SysUserReq req) {
        return ApiResponse.ok(userService.selectAllocatedList(req));
    }

    /**
     * 查询未分配用户角色列表
     */
    @SaCheckPermission("system:role:list")
    @GetMapping("/authUser/unallocatedList")
    public ApiResponse<PageResult<SysUserResp>> unallocatedList(SysUserReq req) {
        return ApiResponse.ok(userService.selectUnallocatedList(req));
    }

    /**
     * 取消授权用户
     */
    @SaCheckPermission("system:role:edit")
    @Log(title = "角色管理", businessType = BusinessType.GRANT)
    @RepeatSubmit()
    @PutMapping("/authUser/cancel")
    public ApiResponse<Void> cancelAuthUser(@RequestBody SysUserRole userRole) {
        return roleService.deleteAuthUser(userRole) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 批量取消授权用户
     *
     * @param roleId  角色ID
     * @param userIds 用户ID串
     */
    @SaCheckPermission("system:role:edit")
    @Log(title = "角色管理", businessType = BusinessType.GRANT)
    @RepeatSubmit()
    @PutMapping("/authUser/cancelAll")
    public ApiResponse<Void> cancelAuthUserAll(Long roleId, Long[] userIds) {
        return roleService.deleteAuthUsers(roleId, userIds) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 批量选择用户授权
     *
     * @param roleId  角色ID
     * @param userIds 用户ID串
     */
    @SaCheckPermission("system:role:edit")
    @Log(title = "角色管理", businessType = BusinessType.GRANT)
    @RepeatSubmit()
    @PutMapping("/authUser/selectAll")
    public ApiResponse<Void> selectAuthUserAll(Long roleId, Long[] userIds) {
        roleService.checkRoleDataScope(roleId);
        return roleService.insertAuthUsers(roleId, userIds) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 获取对应角色部门树列表
     *
     * @param roleId 角色ID
     */
    @SaCheckPermission("system:role:list")
    @GetMapping(value = "/deptTree/{roleId}")
    public ApiResponse<DeptTreeSelectVo> roleDeptTreeselect(@PathVariable("roleId") Long roleId) {
        DeptTreeSelectVo selectVo = new DeptTreeSelectVo(
                deptService.selectDeptListByRoleId(roleId),
                deptService.selectDeptTreeList(new SysDeptReq()));
        return ApiResponse.ok(selectVo);
    }

    /**
     * 角色部门列表树信息
     *
     * @param checkedKeys 选中部门列表
     * @param depts       下拉树结构列表
     */
    public record DeptTreeSelectVo(List<Long> checkedKeys, List<Tree<Long>> depts) {
    }

}
