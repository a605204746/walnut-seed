package com.walnut.seed.module.system.utils;

import com.walnut.seed.common.core.constant.Constants;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.module.system.domain.entity.SysMenu;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 菜单路由辅助工具类
 * <p>
 * 封装菜单构建路由所需的逻辑，保持 SysMenu 实体纯粹。
 *
 * @author deepin_sir
 */
public final class MenuRouteUtils {

    private MenuRouteUtils() {
    }

    /**
     * 菜单节点 — 将菜单与其子节点配对，用于路由构建
     */
    public record MenuNode(SysMenu menu, List<MenuNode> children) {
    }

    /**
     * 获取路由名称（path首字母大写）
     */
    public static String getRouteName(SysMenu menu) {
        String routerName = StringUtils.capitalize(menu.getPath());
        if (isMenuFrame(menu)) {
            routerName = StringUtils.EMPTY;
        }
        return routerName;
    }

    /**
     * 获取路由地址
     */
    public static String getRouterPath(SysMenu menu) {
        String routerPath = menu.getPath();
        // 内链打开外网方式
        if (!Constants.TOP_PARENT_ID.equals(menu.getParentId()) && isInnerLink(menu)) {
            routerPath = innerLinkReplaceEach(routerPath);
        }
        // 非外链并且是一级目录（类型为目录）
        if (Constants.TOP_PARENT_ID.equals(menu.getParentId())
            && SystemConstants.TYPE_DIR.equals(menu.getMenuType())
            && SystemConstants.NO_FRAME.equals(menu.getIsFrame())) {
            routerPath = "/" + menu.getPath();
        }
        // 非外链并且是一级目录（类型为菜单）
        else if (isMenuFrame(menu)) {
            routerPath = "/";
        }
        return routerPath;
    }

    /**
     * 获取组件信息
     */
    public static String getComponentInfo(SysMenu menu) {
        String component = SystemConstants.LAYOUT;
        if (StringUtils.isNotEmpty(menu.getComponent()) && !isMenuFrame(menu)) {
            component = menu.getComponent();
        } else if (StringUtils.isEmpty(menu.getComponent())
            && !Constants.TOP_PARENT_ID.equals(menu.getParentId())
            && isInnerLink(menu)) {
            component = SystemConstants.INNER_LINK;
        } else if (StringUtils.isEmpty(menu.getComponent()) && isParentView(menu)) {
            component = SystemConstants.PARENT_VIEW;
        }
        return component;
    }

    /**
     * 是否为菜单内部跳转
     */
    public static boolean isMenuFrame(SysMenu menu) {
        return Constants.TOP_PARENT_ID.equals(menu.getParentId())
            && SystemConstants.TYPE_MENU.equals(menu.getMenuType())
            && SystemConstants.NO_FRAME.equals(menu.getIsFrame());
    }

    /**
     * 是否为内链组件
     */
    public static boolean isInnerLink(SysMenu menu) {
        return SystemConstants.NO_FRAME.equals(menu.getIsFrame())
            && StringUtils.ishttp(menu.getPath());
    }

    /**
     * 是否为parent_view组件
     */
    public static boolean isParentView(SysMenu menu) {
        return !Constants.TOP_PARENT_ID.equals(menu.getParentId())
            && SystemConstants.TYPE_DIR.equals(menu.getMenuType());
    }

    /**
     * 内链域名特殊字符替换
     */
    public static String innerLinkReplaceEach(String path) {
        return StringUtils.replaceEach(path,
            new String[]{Constants.HTTP, Constants.HTTPS, Constants.WWW, ".", ":"},
            new String[]{"", "", "", "/", "/"});
    }

    /**
     * 根据父ID将扁平菜单列表构建为树结构
     *
     * @param menus    扁平菜单列表
     * @param parentId 顶级父节点ID
     * @return 树形菜单节点列表
     */
    public static List<MenuNode> buildTree(List<SysMenu> menus, Long parentId) {
        Map<Long, List<SysMenu>> grouped = menus.stream()
            .collect(Collectors.groupingBy(SysMenu::getParentId));
        return buildChildren(grouped, parentId);
    }

    private static List<MenuNode> buildChildren(Map<Long, List<SysMenu>> grouped, Long parentId) {
        List<SysMenu> children = grouped.getOrDefault(parentId, List.of());
        List<MenuNode> nodes = new ArrayList<>();
        for (SysMenu child : children) {
            List<MenuNode> grandChildren = buildChildren(grouped, child.getId());
            nodes.add(new MenuNode(child, grandChildren));
        }
        return nodes;
    }
}
