package com.walnut.seed.module.system.service.impl;

import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.satoken.core.service.PermissionService;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.service.SysMenuService;
import com.walnut.seed.module.system.service.SysPermissionService;
import com.walnut.seed.module.system.service.SysRoleService;
import org.springframework.stereotype.Service;

import java.util.HashSet;
import java.util.Set;

/**
 * 用户权限处理
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysPermissionServiceImpl implements SysPermissionService, PermissionService {

    private final SysRoleService roleService;
    private final SysMenuService menuService;

    @Override
    public Set<String> getRolePermission(Long userId) {
        Set<String> roles = new HashSet<>();
        // 管理员拥有所有权限
        if (LoginHelper.isSuperAdmin(userId)) {
            roles.add(SystemConstants.SUPER_ADMIN_ROLE_KEY);
        } else {
            roles.addAll(roleService.selectRolePermissionByUserId(userId));
        }
        return roles;
    }

    @Override
    public Set<String> getMenuPermission(Long userId) {
        Set<String> perms = new HashSet<>();
        // 管理员拥有所有权限
        if (LoginHelper.isSuperAdmin(userId)) {
            perms.add("*:*:*");
        } else {
            perms.addAll(menuService.selectMenuPermsByUserId(userId));
        }
        return perms;
    }
}
