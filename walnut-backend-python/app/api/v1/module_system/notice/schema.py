"""通知公告的入参/出参模型。

notice_content 在库中为 BLOB（UTF-8 字节）：入参接收字符串，出参转回字符串。
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.core.base_schema import PageQueryParam
from app.core.validator import DateTimeStr
from app.utils.xss_util import contains_html


class NoticeQueryParam(PageQueryParam):
    """通知公告列表查询参数（GET）。"""

    notice_title: str | None = Field(default=None, alias="noticeTitle", description="公告标题")
    notice_type: str | None = Field(default=None, alias="noticeType", description="公告类型（1通知 2公告）")
    create_by_name: str | None = Field(default=None, alias="createByName", description="创建人名称")


class NoticeCreateSchema(BaseModel):
    """新增通知公告入参。"""

    model_config = ConfigDict(populate_by_name=True)

    notice_title: str | None = Field(default=None, validate_default=True, alias="noticeTitle", description="公告标题")
    notice_type: str | None = Field(default=None, alias="noticeType", description="公告类型（1通知 2公告）")
    notice_content: str | None = Field(default=None, alias="noticeContent", description="公告内容")
    status: str | None = Field(default=None, description="公告状态（0正常 1关闭）")
    remark: str | None = Field(default=None, description="备注")

    @field_validator("notice_title")
    @classmethod
    def check_notice_title(cls, value: str | None) -> str:
        # 非空、长度上限（50 字符）校验，并拒绝脚本字符（防 XSS）
        if value is None or not value.strip():
            raise ValueError("公告标题不能为空")
        if len(value) > 50:
            raise ValueError("公告标题不能超过50个字符")
        if contains_html(value):
            raise ValueError("公告标题不能包含脚本字符")
        return value


class NoticeUpdateSchema(NoticeCreateSchema):
    """修改通知公告入参。"""

    id: int | None = Field(default=None, validate_default=True, description="公告ID")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("公告ID不能为空")
        return value


class NoticeOutSchema(BaseModel):
    """通知公告出参（notice_content BLOB 转回字符串）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)

    id: int | None = Field(default=None, description="公告ID")
    notice_title: str | None = Field(default=None, description="公告标题")
    notice_type: str | None = Field(default=None, description="公告类型（1通知 2公告）")
    notice_content: str | None = Field(default=None, description="公告内容")
    status: str | None = Field(default=None, description="公告状态（0正常 1关闭）")
    remark: str | None = Field(default=None, description="备注")
    create_by: int | None = Field(default=None, description="创建者")
    create_by_name: str | None = Field(default=None, description="创建人名称")
    create_time: DateTimeStr | None = Field(default=None, description="创建时间")

    @field_validator("notice_content", mode="before")
    @classmethod
    def decode_content(cls, value):
        if isinstance(value, bytes | bytearray):
            return bytes(value).decode("utf-8", errors="replace")
        return value
