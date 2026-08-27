package com.walnut.seed.common.satoken.core.service;

import java.util.Set;

/**
 * 权限服务接口
 *
 * @author deepin_sir
 */
public interface PermissionService {

    /**
     * 获取角色权限列表
     *
     * @param userId 用户ID
     * @return 角色权限集合
     */
    Set<String> getRolePermission(Long userId);

    /**
     * 获取菜单权限列表
     *
     * @param userId 用户ID
     * @return 菜单权限集合
     */
    Set<String> getMenuPermission(Long userId);

}
