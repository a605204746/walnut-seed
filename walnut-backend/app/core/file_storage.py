"""对象存储/文件服务。

支持 ``s3``（默认，任意 S3 兼容对象存储，编排默认为 SeaweedFS，基于 minio SDK）与 ``aliyun``（需安装 oss2）。
上传路径规则：``{yyyy/MM/dd}/{uuid}.{ext}``。

安全约束：
- 上传扩展名白名单（``ALLOWED_EXTENSIONS``）+ 大小上限（``MAX_FILE_SIZE``，分块累计、超限即中止）；
- 下载/内联响应统一携带 ``X-Content-Type-Options: nosniff`` 与 ``Content-Disposition: attachment``
  （img 标签内联渲染不受 attachment 影响，直接导航访问则触发下载而非执行，封堵存储型 XSS）。
"""

import asyncio
import io
import mimetypes
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from typing import Any

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error
from starlette.responses import Response

from app.common.dataclasses import UploadResult
from app.common.enums import HttpStatus
from app.config.setting import settings
from app.core.exceptions import ServiceException
from app.core.logger import logger
from app.utils.i18n import MessageUtils

# 上传分块大小（1MB/块，累计计数用于大小限制）
_UPLOAD_CHUNK_SIZE = 1024 * 1024


def _build_key(filename: str) -> str:
    """生成对象 key：``{yyyy/MM/dd}/{uuid32}.{ext}``。"""
    ext = os.path.splitext(filename)[1]
    return f"{datetime.now():%Y/%m/%d}/{uuid.uuid4().hex}{ext}"


def _check_allowed_extension(filename: str) -> None:
    """上传扩展名白名单校验（无扩展名或不在白名单一律拒绝）。"""
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    allowed = {item.lower() for item in settings.ALLOWED_EXTENSIONS}
    if ext not in allowed:
        raise ServiceException(f"不允许上传的文件扩展名：.{ext or '<空>'}", code=HttpStatus.BAD_REQUEST)


async def _read_upload_with_limit(file: UploadFile) -> bytes:
    """分块读取上传内容并累计计数，超过 ``MAX_FILE_SIZE`` 立即抛业务异常中止。"""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.MAX_FILE_SIZE:
            raise ServiceException(
                MessageUtils.message("upload.exceed.maxSize", settings.MAX_FILE_SIZE // (1024 * 1024)),
                code=HttpStatus.BAD_REQUEST,
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def _read_object_in_thread(obj: Any, chunk_size: int = _UPLOAD_CHUNK_SIZE) -> bytes:
    """同步对象流的线程化分块读取（避免阻塞事件循环）。"""
    chunks: list[bytes] = []
    while True:
        chunk = await asyncio.to_thread(obj.read, chunk_size)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _serve_headers(filename: str | None = None, cacheable: bool = False) -> dict[str, str]:
    """下载/内联响应统一安全头：禁止 MIME 嗅探 + 强制附件下载。"""
    headers = {"X-Content-Type-Options": "nosniff"}
    if filename:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    else:
        headers["Content-Disposition"] = "attachment"
    if cacheable:
        headers["Cache-Control"] = "public, max-age=86400"
    return headers


class FileStorageService(ABC):
    """文件存储接口。"""

    @abstractmethod
    async def upload(self, file: UploadFile) -> UploadResult: ...

    @abstractmethod
    async def download(self, file_url: str) -> Response: ...

    @abstractmethod
    async def delete(self, file_url: str) -> None: ...

    @abstractmethod
    async def serve(self, file_url: str) -> Response:
        """内联读取文件（供图片等浏览器直接渲染）。"""


class S3FileStorageService(FileStorageService):
    """S3 兼容对象存储（默认 SeaweedFS；minio SDK，同步调用经 asyncio.to_thread 包装）。"""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket_name: str, url_prefix: str, secure: bool = False) -> None:
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket_name = bucket_name
        self.url_prefix = url_prefix.rstrip("/")

    def ensure_bucket(self) -> None:
        """桶不存在则创建（幂等）。"""
        if not self._client.bucket_exists(self.bucket_name):
            self._client.make_bucket(self.bucket_name)

    def _key_from_url(self, file_url: str) -> str:
        if self.url_prefix and file_url.startswith(self.url_prefix):
            return file_url[len(self.url_prefix) :].lstrip("/")
        return file_url.lstrip("/")

    async def _get_object(self, key: str):
        try:
            return await asyncio.to_thread(self._client.get_object, self.bucket_name, key)
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise ServiceException("文件不存在", code=HttpStatus.NOT_FOUND) from e
            raise

    async def upload(self, file: UploadFile) -> UploadResult:
        if file is None or not file.filename:
            raise ServiceException("上传文件不能为空", code=HttpStatus.BAD_REQUEST)
        _check_allowed_extension(file.filename)
        key = _build_key(file.filename)
        data = await _read_upload_with_limit(file)
        content_type = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        try:
            await asyncio.to_thread(self._client.put_object, self.bucket_name, key, io.BytesIO(data), len(data), content_type)
        except S3Error as e:
            # 桶缺失时惰性自建一次并重试（启动建桶失败的兜底）
            if e.code == "NoSuchBucket":
                await asyncio.to_thread(self.ensure_bucket)
                await asyncio.to_thread(self._client.put_object, self.bucket_name, key, io.BytesIO(data), len(data), content_type)
            else:
                raise
        return UploadResult(url=f"{self.url_prefix}/{key}", original_filename=file.filename)

    async def download(self, file_url: str) -> Response:
        """附件下载（Content-Disposition: attachment + nosniff）。"""
        key = self._key_from_url(file_url)
        obj = await self._get_object(key)
        try:
            data = await _read_object_in_thread(obj)
            content_type = obj.headers.get("Content-Type") or "application/octet-stream"
        finally:
            obj.close()
            obj.release_conn()
        filename = key.rsplit("/", 1)[-1]
        return Response(content=data, media_type=content_type, headers=_serve_headers(filename))

    async def serve(self, file_url: str) -> Response:
        """内联读取（浏览器直接渲染，如 <img src>；nosniff + attachment 防存储型 XSS）。"""
        key = self._key_from_url(file_url)
        obj = await self._get_object(key)
        try:
            data = await _read_object_in_thread(obj)
            content_type = obj.headers.get("Content-Type") or mimetypes.guess_type(key)[0] or "application/octet-stream"
        finally:
            obj.close()
            obj.release_conn()
        return Response(content=data, media_type=content_type, headers=_serve_headers(cacheable=True))

    async def delete(self, file_url: str) -> None:
        key = self._key_from_url(file_url)
        try:
            await asyncio.to_thread(self._client.remove_object, self.bucket_name, key)
        except Exception as e:
            logger.warning("对象存储删除文件失败: {}", e)


class AliyunFileStorageService(FileStorageService):
    """阿里云 OSS 存储（需安装 oss2）。"""

    def __init__(self, endpoint: str, access_key_id: str, access_key_secret: str, bucket_name: str, url_prefix: str) -> None:
        try:
            import oss2  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ServiceException("阿里云 OSS 需安装 oss2 依赖") from exc
        self._oss2 = oss2
        self.bucket = oss2.Bucket(oss2.Auth(access_key_id, access_key_secret), endpoint, bucket_name)
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self.url_prefix = url_prefix.rstrip("/") if url_prefix else ""

    def _build_url(self, key: str) -> str:
        if self.url_prefix:
            return f"{self.url_prefix}/{key}"
        return f"https://{self.bucket_name}.{self.endpoint}/{key}"

    def _key_from_url(self, file_url: str) -> str:
        if self.url_prefix and file_url.startswith(self.url_prefix):
            return file_url[len(self.url_prefix) :].lstrip("/")
        return file_url

    async def upload(self, file: UploadFile) -> UploadResult:
        if file is None or not file.filename:
            raise ServiceException("上传文件不能为空", code=HttpStatus.BAD_REQUEST)
        _check_allowed_extension(file.filename)
        key = _build_key(file.filename)
        data = await _read_upload_with_limit(file)
        await asyncio.to_thread(self.bucket.put_object, key, data)
        return UploadResult(url=self._build_url(key), original_filename=file.filename)

    async def _read(self, file_url: str) -> bytes:
        obj = await asyncio.to_thread(self.bucket.get_object, self._key_from_url(file_url))
        return await _read_object_in_thread(obj)

    async def download(self, file_url: str) -> Response:
        data = await self._read(file_url)
        return Response(content=data, media_type="application/octet-stream", headers=_serve_headers())

    async def serve(self, file_url: str) -> Response:
        key = self._key_from_url(file_url)
        data = await self._read(file_url)
        return Response(
            content=data,
            media_type=mimetypes.guess_type(key)[0] or "application/octet-stream",
            headers=_serve_headers(cacheable=True),
        )

    async def delete(self, file_url: str) -> None:
        try:
            await asyncio.to_thread(self.bucket.delete_object, self._key_from_url(file_url))
        except Exception as e:
            logger.warning("OSS 删除文件失败: {}", e)


@lru_cache(maxsize=1)
def get_file_storage() -> FileStorageService:
    """按 ``settings.OSS_TYPE`` 返回文件存储实现（单例缓存）。"""
    if settings.OSS_TYPE == "aliyun":
        return AliyunFileStorageService(
            endpoint=settings.OSS_ALIYUN_ENDPOINT,
            access_key_id=settings.OSS_ALIYUN_ACCESS_KEY_ID,
            access_key_secret=settings.OSS_ALIYUN_ACCESS_KEY_SECRET,
            bucket_name=settings.OSS_ALIYUN_BUCKET_NAME,
            url_prefix=settings.OSS_ALIYUN_URL_PREFIX,
        )
    return S3FileStorageService(
        endpoint=settings.OSS_S3_ENDPOINT,
        access_key=settings.OSS_S3_ACCESS_KEY,
        secret_key=settings.OSS_S3_SECRET_KEY,
        bucket_name=settings.OSS_S3_BUCKET_NAME,
        url_prefix=settings.OSS_S3_URL_PREFIX,
        secure=settings.OSS_S3_SECURE,
    )
