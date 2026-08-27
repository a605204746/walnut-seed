package com.walnut.seed.module.system.service;

import cn.hutool.core.lang.tree.Tree;
import com.walnut.seed.module.system.domain.entity.SysMenu;
import com.walnut.seed.module.system.domain.req.SysMenuReq;
import com.walnut.seed.module.system.domain.resp.RouterResp;
import com.walnut.seed.module.system.domain.resp.SysMenuResp;

import java.util.List;
import java.util.Set;

/**
 * 菜单 业务层
 *
 * @author deepin_sir
 */
public interface SysMenuService {

    /**
     * 根据用户查询系统菜单列表
     *
     * @param userId 用户ID
     * @return 菜单列表
     */
    List<SysMenuResp> selectMenuList(Long userId);

    /**
     * 根据用户查询系统菜单列表
     *
     * @param menu   菜单信息
     * @param userId 用户ID
     * @return 菜单列表
     */
    List<SysMenuResp> selectMenuList(SysMenuReq menu, Long userId);

    /**
     * 根据用户ID查询权限
     *
     * @param userId 用户ID
     * @return 权限列表
     */
    Set<String> selectMenuPermsByUserId(Long userId);

    /**
     * 根据角色ID查询权限
     *
     * @param roleId 角色ID
     * @return 权限列表
     */
    Set<String> selectMenuPermsByRoleId(Long roleId);

    /**
     * 根据用户ID查询菜单树信息
     *
     * @param userId 用户ID
     * @return 菜单列表
     */
    List<SysMenu> selectMenuTreeByUserId(Long userId);

    /**
     * 根据角色ID查询菜单树信息
     *
     * @param roleId 角色ID
     * @return 选中菜单列表
     */
    List<Long> selectMenuListByRoleId(Long roleId);

    /**
     * 构建前端路由所需要的菜单
     *
     * @param menus 菜单列表
     * @return 路由列表
     */
    List<RouterResp> buildMenus(List<SysMenu> menus);

    /**
     * 构建前端所需要下拉树结构
     *
     * @param menus 菜单列表
     * @return 下拉树结构列表
     */
    List<Tree<Long>> buildMenuTreeSelect(List<SysMenuResp> menus);

    /**
     * 根据菜单ID查询信息
     *
     * @param menuId 菜单ID
     * @return 菜单信息
     */
    SysMenuResp selectMenuById(Long menuId);

    /**
     * 是否存在菜单子节点
     *
     * @param menuId 菜单ID
     * @return 结果 true 存在 false 不存在
     */
    boolean hasChildByMenuId(Long menuId);

    /**
     * 是否存在菜单子节点
     *
     * @param menuIds 菜单ID串
     * @return 结果 true 存在 false 不存在
     */
    boolean hasChildByMenuId(List<Long> menuIds);

    /**
     * 查询菜单是否存在角色
     *
     * @param menuId 菜单ID
     * @return 结果 true 存在 false 不存在
     */
    boolean checkMenuExistRole(Long menuId);

    /**
     * 新增保存菜单信息
     *
     * @param req 菜单信息
     * @return 结果
     */
    int insertMenu(SysMenuReq req);

    /**
     * 修改保存菜单信息
     *
     * @param req 菜单信息
     * @return 结果
     */
    int updateMenu(SysMenuReq req);

    /**
     * 删除菜单管理信息
     *
     * @param menuId 菜单ID
     * @return 结果
     */
    int deleteMenuById(Long menuId);

    /**
     * 批量删除菜单管理信息
     *
     * @param menuIds 菜单ID串
     * @return 结果
     */
    void deleteMenuById(List<Long> menuIds);

    /**
     * 校验菜单名称是否唯一
     *
     * @param menu 菜单信息
     * @return 结果
     */
    boolean checkMenuNameUnique(SysMenuReq menu);

    /**
     * 校验路由组合是否唯一
     *
     * @param menu 菜单信息
     * @return 结果
     */
    boolean checkRouteConfigUnique(SysMenuReq menu);

}
