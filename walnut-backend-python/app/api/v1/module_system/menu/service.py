"""菜单域业务逻辑。

- ``build_menus``：将扁平菜单构建为前端路由（getRouters）；
- ``build_menu_tree_select``：构建下拉树（treeselect/roleMenuTreeselect）；
- 唯一性/删除校验返回中文业务消息。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.api.v1.module_system.menu.crud import MenuCrud
from app.api.v1.module_system.menu.model import MenuModel
from app.api.v1.module_system.menu.schema import MenuCreateSchema, MenuQuerySchema, MetaResp, RouterResp
from app.common.constant import Constants, SystemConstants
from app.core.base_schema import AuthSchema
from app.utils.string_util import is_empty, is_http, start_with_any_ignore_case


# ==================== 菜单路由辅助 ====================
def _capitalize(value: str | None) -> str:
    """首字母大写（仅大写首字符，其余不变）。"""
    if not value:
        return ""
    return value[0].upper() + value[1:]


def is_menu_frame(menu) -> bool:
    """是否为菜单内部跳转。"""
    return (
        menu.parent_id == Constants.TOP_PARENT_ID
        and menu.menu_type == SystemConstants.TYPE_MENU
        and menu.is_frame == SystemConstants.NO_FRAME
    )


def is_inner_link(menu) -> bool:
    """是否为内链组件。"""
    return menu.is_frame == SystemConstants.NO_FRAME and is_http(menu.path)


def is_parent_view(menu) -> bool:
    """是否为 parent_view 组件。"""
    return menu.parent_id != Constants.TOP_PARENT_ID and menu.menu_type == SystemConstants.TYPE_DIR


def get_route_name(menu) -> str:
    """获取路由名称（path 首字母大写，菜单内部跳转时为空）。"""
    router_name = _capitalize(menu.path)
    if is_menu_frame(menu):
        router_name = ""
    return router_name


def get_router_path(menu) -> str:
    """获取路由地址。"""
    router_path = menu.path
    # 内链打开外网方式
    if menu.parent_id != Constants.TOP_PARENT_ID and is_inner_link(menu):
        router_path = inner_link_replace_each(router_path)
    # 非外链并且是一级目录（类型为目录）
    if (
        menu.parent_id == Constants.TOP_PARENT_ID
        and menu.menu_type == SystemConstants.TYPE_DIR
        and menu.is_frame == SystemConstants.NO_FRAME
    ):
        router_path = "/" + (menu.path or "")
    # 非外链并且是一级目录（类型为菜单）
    elif is_menu_frame(menu):
        router_path = "/"
    return router_path


def get_component_info(menu) -> str:
    """获取组件信息。"""
    component = SystemConstants.LAYOUT
    if not is_empty(menu.component) and not is_menu_frame(menu):
        component = menu.component
    elif is_empty(menu.component) and menu.parent_id != Constants.TOP_PARENT_ID and is_inner_link(menu):
        component = SystemConstants.INNER_LINK
    elif is_empty(menu.component) and is_parent_view(menu):
        component = SystemConstants.PARENT_VIEW
    return component


def inner_link_replace_each(path: str | None) -> str | None:
    """内链域名特殊字符替换。"""
    if not path:
        return path
    for search, replacement in (
        (Constants.HTTP, ""),
        (Constants.HTTPS, ""),
        (Constants.WWW, ""),
        (".", "/"),
        (":", "/"),
    ):
        path = path.replace(search, replacement)
    return path


def _route_name_of(menu) -> str:
    """checkRouteConfigUnique 中的 routeName：getRouteName 为空时回退 path。"""
    route_name = get_route_name(menu)
    return route_name if not is_empty(route_name) else menu.path


def _equals_any_ignore_case(value: str | None, *targets: str | None) -> bool:
    """忽略大小写判断 value 是否等于任一 target。"""
    if value is None:
        return any(t is None for t in targets)
    low = value.lower()
    return any(t is not None and t.lower() == low for t in targets)


def router_to_dict(router: RouterResp) -> dict:
    """将 RouterResp 序列化为 dict，忽略 null、空字符串、空集合；
    布尔（含 false）保留；meta 内部字段全量输出。
    """
    out: dict = {}
    if router.name not in (None, ""):
        out["name"] = router.name
    if router.path not in (None, ""):
        out["path"] = router.path
    if router.hidden is not None:
        out["hidden"] = router.hidden
    if router.redirect not in (None, ""):
        out["redirect"] = router.redirect
    if router.component not in (None, ""):
        out["component"] = router.component
    if router.query not in (None, ""):
        out["query"] = router.query
    if router.always_show is not None:
        out["alwaysShow"] = router.always_show
    if router.meta is not None:
        out["meta"] = router.meta.model_dump(by_alias=True)
    if router.children:
        out["children"] = [router_to_dict(child) for child in router.children]
    return out


@dataclass
class MenuNode:
    """菜单节点 — 将菜单与其子节点配对。"""

    menu: MenuModel
    children: list[MenuNode] = field(default_factory=list)


# ==================== 业务服务 ====================
class MenuService:
    """菜单业务层。"""

    def __init__(self, auth: AuthSchema, db) -> None:
        self.auth = auth
        self.db = db
        self.crud = MenuCrud(MenuModel, auth, db)

    # ---------------- 列表 / 路由查询 ----------------
    async def select_menu_list(self, query: MenuQuerySchema) -> list[MenuModel]:
        return await self.crud.select_menu_list(query)

    async def select_menu_tree_by_user_id(self) -> list[MenuModel]:
        return await self.crud.select_menu_tree_by_user_id()

    async def select_menu_by_id(self, menu_id: int) -> MenuModel | None:
        return await self.crud.select_menu_by_id(menu_id)

    async def select_menu_list_by_role_id(self, role_id: int) -> list[int]:
        return await self.crud.select_menu_list_by_role_id(role_id)

    # ---------------- 构建前端路由 ----------------
    def build_menus(self, menus: list[MenuModel]) -> list[dict]:
        """构建前端路由，返回 RouterResp 的 dict 列表。"""
        tree = self._build_tree(menus, Constants.TOP_PARENT_ID)
        return [router_to_dict(router) for router in self._build_routers(tree)]

    def _build_tree(self, menus: list[MenuModel], parent_id: int) -> list[MenuNode]:
        grouped: dict = {}
        for menu in menus:
            grouped.setdefault(menu.parent_id, []).append(menu)
        return self._build_children(grouped, parent_id)

    def _build_children(self, grouped: dict, parent_id: int) -> list[MenuNode]:
        nodes = []
        for child in grouped.get(parent_id, []):
            nodes.append(MenuNode(menu=child, children=self._build_children(grouped, child.id)))
        return nodes

    def _build_routers(self, nodes: list[MenuNode]) -> list[RouterResp]:
        routers: list[RouterResp] = []
        for node in nodes:
            menu = node.menu
            router = RouterResp(
                hidden=menu.visible == "1",
                name=get_route_name(menu) + str(menu.id),
                path=get_router_path(menu),
                component=get_component_info(menu),
                query=menu.query_param,
                meta=self._build_meta(menu),
            )
            if node.children and menu.menu_type == SystemConstants.TYPE_DIR:
                router.always_show = True
                router.redirect = "noRedirect"
                router.children = self._build_routers(node.children)
            elif is_menu_frame(menu):
                frame_name = _capitalize(menu.path) + str(menu.id)
                router.meta = None
                child = RouterResp(
                    path=menu.path,
                    component=menu.component,
                    name=frame_name,
                    meta=self._build_meta(menu),
                    query=menu.query_param,
                )
                router.children = [child]
            elif menu.parent_id == Constants.TOP_PARENT_ID and is_inner_link(menu):
                router.meta = MetaResp(title=menu.menu_name, icon=menu.icon)
                router.path = "/"
                router_path = inner_link_replace_each(menu.path)
                inner_link_name = _capitalize(router_path) + str(menu.id)
                child = RouterResp(
                    path=router_path,
                    component=SystemConstants.INNER_LINK,
                    name=inner_link_name,
                    meta=MetaResp(title=menu.menu_name, icon=menu.icon, link=menu.path),
                )
                router.children = [child]
            routers.append(router)
        return routers

    def _build_meta(self, menu: MenuModel) -> MetaResp:
        """构建完整 meta。"""
        link = menu.path if is_http(menu.path) else None
        active_menu = menu.remark if start_with_any_ignore_case(menu.remark, "/") else None
        return MetaResp(
            title=menu.menu_name,
            icon=menu.icon,
            no_cache=menu.is_cache == "1",
            link=link,
            active_menu=active_menu,
        )

    # ---------------- 构建下拉树 ----------------
    def build_menu_tree_select(self, menus: list[MenuModel]) -> list[dict]:
        """构建下拉树（节点名称字段为 label）。"""
        if not menus:
            return []
        root_parent_id = menus[0].parent_id
        grouped: dict = {}
        for menu in menus:
            grouped.setdefault(menu.parent_id, []).append(menu)
        return self._build_select_children(grouped, root_parent_id)

    def _build_select_children(self, grouped: dict, parent_id: int | None) -> list[dict]:
        nodes = []
        for menu in grouped.get(parent_id, []):
            node = {
                "id": menu.id,
                "parentId": menu.parent_id,
                "label": menu.menu_name,
                "weight": menu.order_num,
                "menuType": menu.menu_type,
                "icon": menu.icon,
                "visible": menu.visible,
                "status": menu.status,
            }
            children = self._build_select_children(grouped, menu.id)
            if children:
                node["children"] = children
            nodes.append(node)
        return nodes

    # ---------------- 唯一性校验 ----------------
    async def check_menu_name_unique(self, req: MenuCreateSchema) -> bool:
        """校验同级下菜单名称唯一。"""
        assert req.menu_name is not None  # schema 校验（validate_default）保证非空
        exists = await self.crud.exists_menu_name(req.menu_name, req.parent_id, req.id)
        return not exists

    async def check_route_config_unique(self, req: MenuCreateSchema) -> bool:
        """校验路由名称/地址组合唯一。"""
        if req.menu_type == SystemConstants.TYPE_BUTTON:
            return True
        menu_id = req.id if req.id is not None else -1
        parent_id = req.parent_id
        path = req.path
        menu_type = req.menu_type
        route_name = _route_name_of(req)

        candidates = await self.crud.select_route_conflict_candidates(path, route_name)
        for sys_menu in candidates:
            if sys_menu.id == menu_id:
                continue
            db_parent_id = sys_menu.parent_id
            db_path = sys_menu.path
            db_route_name = _route_name_of(sys_menu)
            # 同级路由冲突
            if _equals_any_ignore_case(path, db_path) and parent_id == db_parent_id:
                return False
            # 根目录路由冲突
            if (
                _equals_any_ignore_case(path, db_path)
                and parent_id == Constants.TOP_PARENT_ID
                and db_parent_id == Constants.TOP_PARENT_ID
            ):
                return False
            # 路由名称冲突（需全局唯一）
            if _equals_any_ignore_case(route_name, db_route_name) and sys_menu.menu_type == menu_type:
                return False
        return True

    # ---------------- 删除前置校验 ----------------
    async def has_child_by_menu_id(self, menu_id: int) -> bool:
        return await self.crud.has_child_by_menu_id(menu_id)

    async def has_child_by_menu_ids(self, menu_ids: list[int]) -> bool:
        return await self.crud.has_child_by_menu_ids(menu_ids)

    async def check_menu_exist_role(self, menu_id: int) -> bool:
        return await self.crud.check_menu_exist_role(menu_id)

    # ---------------- 增删改 ----------------
    async def insert_menu(self, req: MenuCreateSchema) -> int:
        data = req.model_dump(exclude_none=True)
        data.pop("id", None)
        menu = MenuModel(**data)
        await self.crud.create(menu)
        return 1

    async def update_menu(self, req: MenuCreateSchema) -> int:
        menu = await self.crud.get(req.id)
        if menu is None:
            return 0
        # 仅更新非空字段
        data = req.model_dump(exclude_none=True)
        data.pop("id", None)
        for field_name, value in data.items():
            setattr(menu, field_name, value)
        await self.crud.update(menu)
        return 1

    async def delete_menu_by_id(self, menu_id: int) -> int:
        return 1 if await self.crud.delete(menu_id) else 0

    async def delete_menu_by_ids(self, menu_ids: list[int]) -> None:
        """级联删除菜单及其角色关联。"""
        await self.crud.delete_batch(menu_ids)
        await self.crud.delete_role_menu_by_menu_ids(menu_ids)
