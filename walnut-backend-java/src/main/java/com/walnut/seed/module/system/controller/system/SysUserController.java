package com.walnut.seed.module.system.controller.system;
import com.walnut.seed.common.core.domain.PageResult;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.hutool.core.lang.tree.Tree;
import cn.hutool.core.util.ArrayUtil;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.crypto.digest.BCrypt;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.module.system.domain.model.LoginUser;
import com.walnut.seed.common.core.utils.StreamUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.encrypt.annotation.ApiEncrypt;
import com.walnut.seed.common.excel.core.ExcelResult;
import com.walnut.seed.common.excel.utils.ExcelUtil;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.common.mybatis.helper.DataPermissionHelper;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.domain.req.SysDeptReq;
import com.walnut.seed.module.system.domain.req.SysPostReq;
import com.walnut.seed.module.system.domain.req.SysRoleReq;
import com.walnut.seed.module.system.domain.req.SysUserReq;
import com.walnut.seed.module.system.domain.resp.*;
import com.walnut.seed.module.system.listener.SysUserImportListener;
import com.walnut.seed.module.system.service.*;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.ArrayList;
import java.util.List;

/**
 * 用户信息
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/user")
public class SysUserController {

    private final SysUserService userService;
    private final SysRoleService roleService;
    private final SysPostService postService;
    private final SysDeptService deptService;

    /**
     * 获取用户列表
     */
    @SaCheckPermission("system:user:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysUserResp>> list(SysUserReq req) {
        return ApiResponse.ok(userService.selectPageUserList(req));
    }

    /**
     * 导出用户列表
     */
    @Log(title = "用户管理", businessType = BusinessType.EXPORT)
    @SaCheckPermission("system:user:export")
    @PostMapping("/export")
    public void export(SysUserReq req, HttpServletResponse response) {
        List<SysUserExportResp> list = userService.selectUserExportList(req);
        ExcelUtil.exportExcel(list, "用户数据", SysUserExportResp.class, response);
    }

    /**
     * 导入数据
     *
     * @param file          导入文件
     * @param updateSupport 是否更新已存在数据
     */
    @Log(title = "用户管理", businessType = BusinessType.IMPORT)
    @SaCheckPermission("system:user:import")
    @PostMapping(value = "/importData", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResponse<Void> importData(@RequestPart("file") MultipartFile file, boolean updateSupport) throws Exception {
        ExcelResult<SysUserImportResp> result = ExcelUtil.importExcel(file.getInputStream(), SysUserImportResp.class, new SysUserImportListener(updateSupport));
        return ApiResponse.ok(result.getAnalysis());
    }

    /**
     * 获取导入模板
     */
    @PostMapping("/importTemplate")
    public void importTemplate(HttpServletResponse response) {
        ExcelUtil.exportExcel(new ArrayList<>(), "用户数据", SysUserImportResp.class, response);
    }

    /**
     * 获取用户信息
     *
     * @return 用户信息
     */
    @GetMapping("/getInfo")
    public ApiResponse<UserInfoResp> get() {
        UserInfoResp userInfoVo = new UserInfoResp();
        LoginUser loginUser = LoginHelper.getLoginUser();
        SysUserResp user = DataPermissionHelper.ignore(() -> userService.selectUserById(loginUser.getUserId()));
        if (ObjectUtil.isNull(user)) {
            return ApiResponse.fail("没有权限访问用户数据!");
        }
        userInfoVo.setUser(user);
        userInfoVo.setPermissions(loginUser.getMenuPermission());
        userInfoVo.setRoles(loginUser.getRolePermission());
        return ApiResponse.ok(userInfoVo);
    }

    /**
     * 根据用户编号获取详细信息
     *
     * @param userId 用户ID
     */
    @SaCheckPermission("system:user:query")
    @GetMapping(value = {"/", "/{userId}"})
    public ApiResponse<SysUserInfoResp> get(@PathVariable(value = "userId", required = false) Long userId) {
        SysUserInfoResp userInfoVo = new SysUserInfoResp();
        if (ObjectUtil.isNotNull(userId)) {
            userService.checkUserDataScope(userId);
            SysUserResp sysUser = userService.selectUserById(userId);
            userInfoVo.setUser(sysUser);
            userInfoVo.setRoleIds(roleService.selectRoleListByUserId(userId));
            Long deptId = sysUser.getDeptId();
            if (ObjectUtil.isNotNull(deptId)) {
                SysPostReq postBo = new SysPostReq();
                postBo.setDeptId(deptId);
                userInfoVo.setPosts(postService.selectPostList(postBo));
                userInfoVo.setPostIds(postService.selectPostListByUserId(userId));
            }
        }
        SysRoleReq roleBo = new SysRoleReq();
        roleBo.setStatus(SystemConstants.NORMAL);
        List<SysRoleResp> roles = roleService.selectRoleList(roleBo);
        userInfoVo.setRoles(LoginHelper.isSuperAdmin(userId) ? roles : StreamUtils.filter(roles, r -> !r.isSuperAdmin()));
        return ApiResponse.ok(userInfoVo);
    }

    /**
     * 新增用户
     */
    @SaCheckPermission("system:user:add")
    @Log(title = "用户管理", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping
    public ApiResponse<Void> create(@Validated @RequestBody SysUserReq req) {
        deptService.checkDeptDataScope(req.getDeptId());
        if (!userService.checkUserNameUnique(req)) {
            return ApiResponse.fail("新增用户'" + req.getUserName() + "'失败，登录账号已存在");
        } else if (StringUtils.isNotEmpty(req.getPhonenumber()) && !userService.checkPhoneUnique(req)) {
            return ApiResponse.fail("新增用户'" + req.getUserName() + "'失败，手机号码已存在");
        } else if (StringUtils.isNotEmpty(req.getEmail()) && !userService.checkEmailUnique(req)) {
            return ApiResponse.fail("新增用户'" + req.getUserName() + "'失败，邮箱账号已存在");
        }
        req.setPassword(BCrypt.hashpw(req.getPassword()));
        return userService.insertUser(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 修改用户
     */
    @SaCheckPermission("system:user:edit")
    @Log(title = "用户管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping
    public ApiResponse<Void> update(@Validated @RequestBody SysUserReq req) {
        userService.checkUserAllowed(req.getId());
        userService.checkUserDataScope(req.getId());
        deptService.checkDeptDataScope(req.getDeptId());
        if (!userService.checkUserNameUnique(req)) {
            return ApiResponse.fail("修改用户'" + req.getUserName() + "'失败，登录账号已存在");
        } else if (StringUtils.isNotEmpty(req.getPhonenumber()) && !userService.checkPhoneUnique(req)) {
            return ApiResponse.fail("修改用户'" + req.getUserName() + "'失败，手机号码已存在");
        } else if (StringUtils.isNotEmpty(req.getEmail()) && !userService.checkEmailUnique(req)) {
            return ApiResponse.fail("修改用户'" + req.getUserName() + "'失败，邮箱账号已存在");
        }
        return userService.updateUser(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 删除用户
     *
     * @param userIds 角色ID串
     */
    @SaCheckPermission("system:user:remove")
    @Log(title = "用户管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{userIds}")
    public ApiResponse<Void> delete(@PathVariable Long[] userIds) {
        if (ArrayUtil.contains(userIds, LoginHelper.getUserId())) {
            return ApiResponse.fail("当前用户不能删除");
        }
        return userService.deleteUserByIds(userIds) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 根据用户ID串批量获取用户基础信息
     *
     * @param userIds 用户ID串
     * @param deptId  部门ID
     */
    @SaCheckPermission("system:user:query")
    @GetMapping("/optionselect")
    public ApiResponse<List<SysUserResp>> optionselect(@RequestParam(required = false) Long[] userIds,
                                           @RequestParam(required = false) Long deptId) {
        return ApiResponse.ok(userService.selectUserByIds(ArrayUtil.isEmpty(userIds) ? null : List.of(userIds), deptId));
    }

    /**
     * 重置密码
     */
    @ApiEncrypt
    @SaCheckPermission("system:user:resetPwd")
    @Log(title = "用户管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping("/resetPwd")
    public ApiResponse<Void> resetPwd(@RequestBody SysUserReq req) {
        userService.checkUserAllowed(req.getId());
        userService.checkUserDataScope(req.getId());
        req.setPassword(BCrypt.hashpw(req.getPassword()));
        return userService.resetUserPwd(req.getId(), req.getPassword()) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 状态修改
     */
    @SaCheckPermission("system:user:edit")
    @Log(title = "用户管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping("/changeStatus")
    public ApiResponse<Void> changeStatus(@RequestBody SysUserReq req) {
        userService.checkUserAllowed(req.getId());
        userService.checkUserDataScope(req.getId());
        return userService.updateUserStatus(req.getId(), req.getStatus()) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 根据用户编号获取授权角色
     *
     * @param userId 用户ID
     */
    @SaCheckPermission("system:user:query")
    @GetMapping("/authRole/{userId}")
    public ApiResponse<SysUserInfoResp> authRole(@PathVariable Long userId) {
        userService.checkUserDataScope(userId);
        SysUserResp user = userService.selectUserById(userId);
        List<SysRoleResp> roles = roleService.selectRolesAuthByUserId(userId);
        SysUserInfoResp userInfoVo = new SysUserInfoResp();
        userInfoVo.setUser(user);
        userInfoVo.setRoles(LoginHelper.isSuperAdmin(userId) ? roles : StreamUtils.filter(roles, r -> !r.isSuperAdmin()));
        return ApiResponse.ok(userInfoVo);
    }

    /**
     * 用户授权角色
     *
     * @param userId  用户Id
     * @param roleIds 角色ID串
     */
    @SaCheckPermission("system:user:edit")
    @Log(title = "用户管理", businessType = BusinessType.GRANT)
    @RepeatSubmit()
    @PutMapping("/authRole")
    public ApiResponse<Void> insertAuthRole(Long userId, Long[] roleIds) {
        userService.checkUserDataScope(userId);
        userService.insertUserAuth(userId, roleIds);
        return ApiResponse.ok();
    }

    /**
     * 获取部门树列表
     */
    @SaCheckPermission("system:user:list")
    @GetMapping("/deptTree")
    public ApiResponse<List<Tree<Long>>> deptTree(SysDeptReq req) {
        return ApiResponse.ok(deptService.selectDeptTreeList(req));
    }

    /**
     * 获取部门下的所有用户信息
     */
    @SaCheckPermission("system:user:list")
    @GetMapping("/list/dept/{deptId}")
    public ApiResponse<List<SysUserResp>> listByDept(@PathVariable @NotNull Long deptId) {
        return ApiResponse.ok(userService.selectUserListByDept(deptId));
    }

}
