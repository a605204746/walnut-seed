package com.walnut.seed.module.system.controller.system;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.annotation.SaCheckRole;
import cn.dev33.satoken.annotation.SaMode;
import cn.hutool.core.lang.tree.Tree;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.domain.entity.SysMenu;
import com.walnut.seed.module.system.domain.req.SysMenuReq;
import com.walnut.seed.module.system.domain.resp.RouterResp;
import com.walnut.seed.module.system.domain.resp.SysMenuResp;
import com.walnut.seed.module.system.service.SysMenuService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 菜单信息
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/menu")
public class SysMenuController {

    private final SysMenuService menuService;

    /**
     * 获取路由信息
     *
     * @return 路由信息
     */
    @GetMapping("/getRouters")
    public ApiResponse<List<RouterResp>> getRouters() {
        List<SysMenu> menus = menuService.selectMenuTreeByUserId(LoginHelper.getUserId());
        return ApiResponse.ok(menuService.buildMenus(menus));
    }

    /**
     * 获取菜单列表
     */
    @SaCheckRole(value = {SystemConstants.SUPER_ADMIN_ROLE_KEY}, mode = SaMode.OR)
    @SaCheckPermission("system:menu:list")
    @GetMapping("/list")
    public ApiResponse<List<SysMenuResp>> list(SysMenuReq req) {
        List<SysMenuResp> menus = menuService.selectMenuList(req, LoginHelper.getUserId());
        return ApiResponse.ok(menus);
    }

    /**
     * 根据菜单编号获取详细信息
     *
     * @param menuId 菜单ID
     */
    @SaCheckRole(value = {SystemConstants.SUPER_ADMIN_ROLE_KEY}, mode = SaMode.OR)
    @SaCheckPermission("system:menu:query")
    @GetMapping(value = "/{menuId}")
    public ApiResponse<SysMenuResp> get(@PathVariable Long menuId) {
        return ApiResponse.ok(menuService.selectMenuById(menuId));
    }

    /**
     * 获取菜单下拉树列表
     */
    @SaCheckPermission("system:menu:query")
    @GetMapping("/treeselect")
    public ApiResponse<List<Tree<Long>>> treeselect(SysMenuReq req) {
        List<SysMenuResp> menus = menuService.selectMenuList(req, LoginHelper.getUserId());
        return ApiResponse.ok(menuService.buildMenuTreeSelect(menus));
    }

    /**
     * 加载对应角色菜单列表树
     *
     * @param roleId 角色ID
     */
    @SaCheckPermission("system:menu:query")
    @GetMapping(value = "/roleMenuTreeselect/{roleId}")
    public ApiResponse<MenuTreeSelectVo> roleMenuTreeselect(@PathVariable("roleId") Long roleId) {
        List<SysMenuResp> menus = menuService.selectMenuList(LoginHelper.getUserId());
        MenuTreeSelectVo selectVo = new MenuTreeSelectVo(
            menuService.selectMenuListByRoleId(roleId),
            menuService.buildMenuTreeSelect(menus));
        return ApiResponse.ok(selectVo);
    }

    /**
     * 新增菜单
     */
    @SaCheckRole(SystemConstants.SUPER_ADMIN_ROLE_KEY)
    @SaCheckPermission("system:menu:add")
    @Log(title = "菜单管理", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping
    public ApiResponse<Void> create(@Validated @RequestBody SysMenuReq req) {
        if (!menuService.checkMenuNameUnique(req)) {
            return ApiResponse.fail("新增菜单'" + req.getMenuName() + "'失败，菜单名称已存在");
        } else if (SystemConstants.YES_FRAME.equals(req.getIsFrame()) && !StringUtils.ishttp(req.getPath())) {
            return ApiResponse.fail("新增菜单'" + req.getMenuName() + "'失败，地址必须以http(s)://开头");
        } else if (!menuService.checkRouteConfigUnique(req)) {
            return ApiResponse.fail("新增菜单'" + req.getMenuName() + "'失败，路由名称或地址已存在");
        }
        return menuService.insertMenu(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 修改菜单
     */
    @SaCheckRole(SystemConstants.SUPER_ADMIN_ROLE_KEY)
    @SaCheckPermission("system:menu:edit")
    @Log(title = "菜单管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping
    public ApiResponse<Void> update(@Validated @RequestBody SysMenuReq req) {
        if (!menuService.checkMenuNameUnique(req)) {
            return ApiResponse.fail("修改菜单'" + req.getMenuName() + "'失败，菜单名称已存在");
        } else if (SystemConstants.YES_FRAME.equals(req.getIsFrame()) && !StringUtils.ishttp(req.getPath())) {
            return ApiResponse.fail("修改菜单'" + req.getMenuName() + "'失败，地址必须以http(s)://开头");
        } else if (req.getId().equals(req.getParentId())) {
            return ApiResponse.fail("修改菜单'" + req.getMenuName() + "'失败，上级菜单不能选择自己");
        } else if (!menuService.checkRouteConfigUnique(req)) {
            return ApiResponse.fail("修改菜单'" + req.getMenuName() + "'失败，路由名称或地址已存在");
        }
        return menuService.updateMenu(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 删除菜单
     *
     * @param menuId 菜单ID
     */
    @SaCheckRole(SystemConstants.SUPER_ADMIN_ROLE_KEY)
    @SaCheckPermission("system:menu:remove")
    @Log(title = "菜单管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{menuId}")
    public ApiResponse<Void> delete(@PathVariable("menuId") Long menuId) {
        if (menuService.hasChildByMenuId(menuId)) {
            return ApiResponse.warn("存在子菜单,不允许删除");
        }
        if (menuService.checkMenuExistRole(menuId)) {
            return ApiResponse.warn("菜单已分配,不允许删除");
        }
        return menuService.deleteMenuById(menuId) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 角色菜单列表树信息
     *
     * @param checkedKeys 选中菜单列表
     * @param menus       菜单下拉树结构列表
     */
    public record MenuTreeSelectVo(List<Long> checkedKeys, List<Tree<Long>> menus) {
    }

    /**
     * 批量级联删除菜单
     *
     * @param menuIds 菜单ID串
     */
    @SaCheckRole(SystemConstants.SUPER_ADMIN_ROLE_KEY)
    @SaCheckPermission("system:menu:remove")
    @Log(title = "菜单管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/cascade/{menuIds}")
    public ApiResponse<Void> delete(@PathVariable("menuIds") Long[] menuIds) {
        List<Long> menuIdList = List.of(menuIds);
        if (menuService.hasChildByMenuId(menuIdList)) {
            return ApiResponse.warn("存在子菜单,不允许删除");
        }
        menuService.deleteMenuById(menuIdList);
        return ApiResponse.ok();
    }

}
