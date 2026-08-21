from fastapi import APIRouter, Depends, UploadFile

from app.common.dataclasses import UploadResult
from app.common.enums import BusinessType
from app.common.response import SuccessResponse
from app.core.dependencies import AuthPermission
from app.core.file_storage import get_file_storage
from app.core.router_class import OperationLogRoute, log

FileRouter = APIRouter(route_class=OperationLogRoute, prefix="/file", tags=["文件管理"])


@FileRouter.post("/upload", summary="文件上传", dependencies=[Depends(AuthPermission())])
@log(title="文件上传", business_type=BusinessType.INSERT)
async def upload(file: UploadFile) -> SuccessResponse:
    result: UploadResult = await get_file_storage().upload(file)
    return SuccessResponse(data=result.model_dump(), msg="上传成功")


@FileRouter.get("/download", summary="文件下载", dependencies=[Depends(AuthPermission())])
async def download(file_url: str):
    return await get_file_storage().download(file_url)


@FileRouter.delete("/delete", summary="文件删除", dependencies=[Depends(AuthPermission())])
@log(title="文件删除", business_type=BusinessType.DELETE)
async def delete(file_url: str) -> SuccessResponse:
    await get_file_storage().delete(file_url)
    return SuccessResponse(msg="删除成功")


# 上传文件内联访问路由（挂在应用根路径，见 app/api/v1/router.py）：
# 替代原 local 方案的 /upload 静态挂载，对象经后端从对象存储（默认 SeaweedFS）流式返回，
# 浏览器通过 /api（vite 代理）或 /prod-api（nginx 代理）前缀访问。
# 与静态挂载同等的公开语义（无鉴权），url 即存储返回的地址。
FileServeRouter = APIRouter(tags=["文件访问"])


@FileServeRouter.get("/upload/{file_path:path}", summary="上传文件访问（内联）", include_in_schema=False)
async def serve_uploaded(file_path: str):
    return await get_file_storage().serve(file_path)
