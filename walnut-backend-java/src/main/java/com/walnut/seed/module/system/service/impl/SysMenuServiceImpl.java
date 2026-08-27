package com.walnut.seed.module.system.service.impl;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.lang.tree.Tree;
import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import com.walnut.seed.common.core.constant.Constants;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.core.utils.TreeBuildUtils;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.domain.entity.SysMenu;
import com.walnut.seed.module.system.domain.entity.SysRole;
import com.walnut.seed.module.system.domain.entity.SysRoleMenu;
import com.walnut.seed.module.system.domain.req.SysMenuReq;
import com.walnut.seed.module.system.domain.resp.MetaResp;
import com.walnut.seed.module.system.domain.resp.RouterResp;
import com.walnut.seed.module.system.domain.resp.SysMenuResp;
import com.walnut.seed.module.system.mapper.SysMenuMapper;
import com.walnut.seed.module.system.mapper.SysRoleMapper;
import com.walnut.seed.module.system.mapper.SysRoleMenuMapper;
import com.walnut.seed.module.system.service.SysMenuService;
import com.walnut.seed.module.system.utils.MenuRouteUtils;
import com.walnut.seed.module.system.utils.MenuRouteUtils.MenuNode;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * 菜单 业务层处理
 *
 * @author deepin_sir
 */
@Slf4j
@RequiredArgsConstructor
@Service
public class SysMenuServiceImpl implements SysMenuService {

    private final SysMenuMapper baseMapper;
    private final SysRoleMapper roleMapper;
    private final SysRoleMenuMapper roleMenuMapper;

    @Override
    public List<SysMenuResp> selectMenuList(Long userId) {
        return selectMenuList(new SysMenuReq(), userId);
    }

    @Override
    public List<SysMenuResp> selectMenuList(SysMenuReq req, Long userId) {
        List<SysMenuResp> menuList;
        LambdaQueryWrapper<SysMenu> wrapper = new LambdaQueryWrapper<>();
        // 管理员显示所有菜单信息 不是管理员 按用户id过滤菜单
        if (!LoginHelper.isSuperAdmin(userId)) {
            // 通过用户id获取角色id 通过角色id获取菜单id 然后in菜单
            wrapper.inSql(SysMenu::getId, baseMapper.buildMenuByUserSql(userId));
        }
        menuList = baseMapper.selectVoList(
            wrapper.like(StringUtils.isNotBlank(req.getMenuName()), SysMenu::getMenuName, req.getMenuName())
                .eq(StringUtils.isNotBlank(req.getVisible()), SysMenu::getVisible, req.getVisible())
                .eq(StringUtils.isNotBlank(req.getStatus()), SysMenu::getStatus, req.getStatus())
                .eq(StringUtils.isNotBlank(req.getMenuType()), SysMenu::getMenuType, req.getMenuType())
                .eq(ObjectUtil.isNotNull(req.getParentId()), SysMenu::getParentId, req.getParentId())
                .orderByAsc(SysMenu::getParentId)
                .orderByAsc(SysMenu::getOrderNum));
        return menuList;
    }

    @Override
    public Set<String> selectMenuPermsByUserId(Long userId) {
        return baseMapper.selectMenuPermsByUserId(userId);
    }

    @Override
    public Set<String> selectMenuPermsByRoleId(Long roleId) {
        return baseMapper.selectMenuPermsByRoleId(roleId);
    }

    @Override
    public List<SysMenu> selectMenuTreeByUserId(Long userId) {
        if (LoginHelper.isSuperAdmin(userId)) {
            return baseMapper.selectMenuTreeAll();
        }
        LambdaQueryWrapper<SysMenu> wrapper = new LambdaQueryWrapper<>();
        return baseMapper.selectList(
            wrapper.in(SysMenu::getMenuType, SystemConstants.TYPE_DIR, SystemConstants.TYPE_MENU)
                .eq(SysMenu::getStatus, SystemConstants.NORMAL)
                .inSql(SysMenu::getId, baseMapper.buildMenuByUserSql(userId))
                .orderByAsc(SysMenu::getParentId)
                .orderByAsc(SysMenu::getOrderNum));
    }

    @Override
    public List<Long> selectMenuListByRoleId(Long roleId) {
        SysRole role = roleMapper.selectById(roleId);
        return baseMapper.selectMenuListByRoleId(roleId, role.getMenuCheckStrictly());
    }

    @Override
    public List<RouterResp> buildMenus(List<SysMenu> menus) {
        List<MenuNode> tree = MenuRouteUtils.buildTree(menus, Constants.TOP_PARENT_ID);
        return buildRouters(tree);
    }

    private List<RouterResp> buildRouters(List<MenuNode> nodes) {
        List<RouterResp> routers = new ArrayList<>();
        for (MenuNode node : nodes) {
            SysMenu menu = node.menu();
            String name = MenuRouteUtils.getRouteName(menu) + menu.getId();
            RouterResp router = new RouterResp();
            router.setHidden("1".equals(menu.getVisible()));
            router.setName(name);
            router.setPath(MenuRouteUtils.getRouterPath(menu));
            router.setComponent(MenuRouteUtils.getComponentInfo(menu));
            router.setQuery(menu.getQueryParam());
            router.setMeta(new MetaResp(menu.getMenuName(), menu.getIcon(), StringUtils.equals("1", menu.getIsCache()), menu.getPath(), menu.getRemark()));
            if (CollUtil.isNotEmpty(node.children()) && SystemConstants.TYPE_DIR.equals(menu.getMenuType())) {
                router.setAlwaysShow(true);
                router.setRedirect("noRedirect");
                router.setChildren(buildRouters(node.children()));
            } else if (MenuRouteUtils.isMenuFrame(menu)) {
                String frameName = StringUtils.capitalize(menu.getPath()) + menu.getId();
                router.setMeta(null);
                List<RouterResp> childrenList = new ArrayList<>();
                RouterResp children = new RouterResp();
                children.setPath(menu.getPath());
                children.setComponent(menu.getComponent());
                children.setName(frameName);
                children.setMeta(new MetaResp(menu.getMenuName(), menu.getIcon(), StringUtils.equals("1", menu.getIsCache()), menu.getPath(), menu.getRemark()));
                children.setQuery(menu.getQueryParam());
                childrenList.add(children);
                router.setChildren(childrenList);
            } else if (menu.getParentId().equals(Constants.TOP_PARENT_ID) && MenuRouteUtils.isInnerLink(menu)) {
                router.setMeta(new MetaResp(menu.getMenuName(), menu.getIcon()));
                router.setPath("/");
                List<RouterResp> childrenList = new ArrayList<>();
                RouterResp children = new RouterResp();
                String routerPath = MenuRouteUtils.innerLinkReplaceEach(menu.getPath());
                String innerLinkName = StringUtils.capitalize(routerPath) + menu.getId();
                children.setPath(routerPath);
                children.setComponent(SystemConstants.INNER_LINK);
                children.setName(innerLinkName);
                children.setMeta(new MetaResp(menu.getMenuName(), menu.getIcon(), menu.getPath()));
                childrenList.add(children);
                router.setChildren(childrenList);
            }
            routers.add(router);
        }
        return routers;
    }

    @Override
    public List<Tree<Long>> buildMenuTreeSelect(List<SysMenuResp> menus) {
        if (CollUtil.isEmpty(menus)) {
            return CollUtil.newArrayList();
        }
        return TreeBuildUtils.build(menus, (menu, tree) -> {
            Tree<Long> menuTree = tree.setId(menu.getId())
                .setParentId(menu.getParentId())
                .setName(menu.getMenuName())
                .setWeight(menu.getOrderNum());
            menuTree.put("menuType", menu.getMenuType());
            menuTree.put("icon", menu.getIcon());
            menuTree.put("visible", menu.getVisible());
            menuTree.put("status", menu.getStatus());
        });
    }

    @Override
    public SysMenuResp selectMenuById(Long menuId) {
        return baseMapper.selectVoById(menuId);
    }

    @Override
    public boolean hasChildByMenuId(Long menuId) {
        return baseMapper.exists(new LambdaQueryWrapper<SysMenu>().eq(SysMenu::getParentId, menuId));
    }

    @Override
    public boolean hasChildByMenuId(List<Long> menuIds) {
        return baseMapper.exists(new LambdaQueryWrapper<SysMenu>().in(SysMenu::getParentId, menuIds).notIn(SysMenu::getId, menuIds));
    }

    @Override
    public boolean checkMenuExistRole(Long menuId) {
        return roleMenuMapper.exists(new LambdaQueryWrapper<SysRoleMenu>().eq(SysRoleMenu::getMenuId, menuId));
    }

    @Override
    public int insertMenu(SysMenuReq req) {
        SysMenu menu = MapstructUtils.convert(req, SysMenu.class);
        return baseMapper.insert(menu);
    }

    @Override
    public int updateMenu(SysMenuReq req) {
        SysMenu menu = MapstructUtils.convert(req, SysMenu.class);
        return baseMapper.updateById(menu);
    }

    @Override
    public int deleteMenuById(Long menuId) {
        return baseMapper.deleteById(menuId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteMenuById(List<Long> menuIds) {
        baseMapper.deleteByIds(menuIds);
        roleMenuMapper.deleteByMenuIds(menuIds);
    }

    @Override
    public boolean checkMenuNameUnique(SysMenuReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysMenu>()
            .eq(SysMenu::getMenuName, req.getMenuName())
            .eq(SysMenu::getParentId, req.getParentId())
            .ne(ObjectUtil.isNotNull(req.getId()), SysMenu::getId, req.getId()));
        return !exist;
    }

    @Override
    public boolean checkRouteConfigUnique(SysMenuReq menuBo) {
        SysMenu menu = MapstructUtils.convert(menuBo, SysMenu.class);
        if (SystemConstants.TYPE_BUTTON.equals(menu.getMenuType())) {
            return true;
        }
        long menuId = ObjectUtil.isNull(menu.getId()) ? -1L : menu.getId();
        Long parentId = menu.getParentId();
        String path = menu.getPath();
        String routeName = StringUtils.isEmpty(MenuRouteUtils.getRouteName(menu)) ? path : MenuRouteUtils.getRouteName(menu);
        List<SysMenu> sysMenuList = baseMapper.selectList(
            new LambdaQueryWrapper<SysMenu>()
                .in(SysMenu::getMenuType, SystemConstants.TYPE_DIR, SystemConstants.TYPE_MENU)
                .and(w ->
                    w.eq(SysMenu::getPath, path).or().eq(SysMenu::getPath, routeName)
                ));
        for (SysMenu sysMenu : sysMenuList) {
            if (!sysMenu.getId().equals(menuId)) {
                Long dbParentId = sysMenu.getParentId();
                String dbPath = sysMenu.getPath();
                String dbRouteName = StringUtils.isEmpty(MenuRouteUtils.getRouteName(sysMenu)) ? dbPath : MenuRouteUtils.getRouteName(sysMenu);
                if (StringUtils.equalsAnyIgnoreCase(path, dbPath) && parentId.equals(dbParentId)) {
                    log.warn("[同级路由冲突] 同级下已存在相同路由路径 '{}'，冲突菜单：{}", dbPath, sysMenu.getMenuName());
                    return false;
                } else if (StringUtils.equalsAnyIgnoreCase(path, dbPath)
                    && Constants.TOP_PARENT_ID.equals(parentId)
                    && Constants.TOP_PARENT_ID.equals(dbParentId)) {
                    log.warn("[根目录路由冲突] 根目录下路由 '{}' 必须唯一，已被菜单 '{}' 占用", path, sysMenu.getMenuName());
                    return false;
                } else if (StringUtils.equalsAnyIgnoreCase(routeName, dbRouteName)
                    && sysMenu.getMenuType().equals(menu.getMenuType())) {
                    log.warn("[路由名称冲突] 路由名称 '{}' 需全局唯一，已被菜单 '{}' 使用", routeName, sysMenu.getMenuName());
                    return false;
                }
            }
        }
        return true;
    }

}
