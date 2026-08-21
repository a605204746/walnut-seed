"""API v1 路由装配（单一组合根）。

各业务模块的 ``__init__.py`` 仅保留包声明，路由前缀、注册顺序等
装配约束集中在此处维护；``init_app.register_routers`` 只从本模块导入。
"""

from fastapi import APIRouter

from app.api.v1.module_common.file.controller import FileRouter, FileServeRouter
from app.api.v1.module_common.health import HealthRouter
from app.api.v1.module_resource.controller import ResourceRouter
from app.api.v1.module_system.client.controller import ClientRouter
from app.api.v1.module_system.config.controller import ConfigRouter
from app.api.v1.module_system.dept.controller import DeptRouter
from app.api.v1.module_system.dict.controller import DictDataRouter, DictTypeRouter
from app.api.v1.module_system.log.controller import LogininforRouter, OperLogRouter
from app.api.v1.module_system.menu.controller import MenuRouter
from app.api.v1.module_system.notice.controller import NoticeRouter
from app.api.v1.module_system.post.controller import PostRouter
from app.api.v1.module_system.role.controller import RoleRouter
from app.api.v1.module_system.social.controller import SocialRouter
from app.api.v1.module_system.user.controller import ProfileRouter, UserRouter
from app.api.v1.module_web.auth.controller import AuthRouter

# ==================== common ====================
common_router = APIRouter(prefix="/common")
common_router.include_router(HealthRouter)
common_router.include_router(FileRouter)

# ==================== upload（应用根路径） ====================
# /upload/{key} 内联访问上传文件（后端从对象存储流式返回），
# 浏览器经 /api（vite）或 /prod-api（nginx）代理前缀访问，无前缀挂载
upload_router = FileServeRouter

# ==================== resource ====================
# ResourceRouter 已带 /resource 前缀（/resource/sse、/resource/websocket）
resource_router = ResourceRouter

# ==================== system ====================
system_router = APIRouter(prefix="/system")
system_router.include_router(PostRouter)
system_router.include_router(DictTypeRouter)
system_router.include_router(DictDataRouter)
system_router.include_router(ConfigRouter)
system_router.include_router(NoticeRouter)
system_router.include_router(ClientRouter)
system_router.include_router(DeptRouter)
system_router.include_router(MenuRouter)
system_router.include_router(RoleRouter)
# Profile 须先于 User 注册，避免 UserRouter 的 /{userId} 吞掉 /user/profile
system_router.include_router(ProfileRouter)
system_router.include_router(UserRouter)

# 以下 Router 自带完整前缀（/system/social、/monitor/*），挂载到应用根
social_router = SocialRouter
monitor_router = APIRouter()
monitor_router.include_router(OperLogRouter)
monitor_router.include_router(LogininforRouter)

# ==================== web ====================
web_router = APIRouter()
web_router.include_router(AuthRouter)


@web_router.get("/", include_in_schema=False, summary="首页提示")
async def index() -> str:
    return "欢迎使用 WalnutSeed 后台管理框架，请通过前端地址访问。"


__all__ = ["common_router", "monitor_router", "resource_router", "social_router", "system_router", "upload_router", "web_router"]
