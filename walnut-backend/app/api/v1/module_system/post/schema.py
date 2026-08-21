"""岗位的入参/出参模型。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.core.base_schema import PageQueryParam
from app.core.validator import DateStr, DateTimeStr


class PostQueryParam(PageQueryParam):
    """岗位列表查询参数（GET）。"""

    dept_id: int | None = Field(default=None, alias="deptId", description="部门id（单部门）")
    belong_dept_id: int | None = Field(default=None, alias="belongDeptId", description="归属部门id（部门树）")
    post_code: str | None = Field(default=None, alias="postCode", description="岗位编码")
    post_category: str | None = Field(default=None, alias="postCategory", description="岗位类别编码")
    post_name: str | None = Field(default=None, alias="postName", description="岗位名称")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")
    begin_time: DateStr | None = Field(default=None, alias="beginTime", description="开始时间")
    end_time: DateStr | None = Field(default=None, alias="endTime", description="结束时间")


class DeptTreeQueryParam(BaseModel):
    """部门树查询参数（GET /post/deptTree）。"""

    model_config = ConfigDict(populate_by_name=True)

    id: int | None = Field(default=None, description="部门ID")
    parent_id: int | None = Field(default=None, alias="parentId", description="父部门ID")
    belong_dept_id: int | None = Field(default=None, alias="belongDeptId", description="归属部门id（部门树）")
    dept_name: str | None = Field(default=None, alias="deptName", description="部门名称")
    dept_category: str | None = Field(default=None, alias="deptCategory", description="部门类别编码")
    status: str | None = Field(default=None, description="部门状态（0正常 1停用）")
    begin_time: DateStr | None = Field(default=None, alias="beginTime", description="开始时间")
    end_time: DateStr | None = Field(default=None, alias="endTime", description="结束时间")


class PostCreateSchema(BaseModel):
    """新增岗位入参。"""

    model_config = ConfigDict(populate_by_name=True)

    dept_id: int | None = Field(default=None, validate_default=True, alias="deptId", description="部门id")
    post_code: str | None = Field(default=None, validate_default=True, alias="postCode", description="岗位编码")
    post_name: str | None = Field(default=None, validate_default=True, alias="postName", description="岗位名称")
    post_category: str | None = Field(default=None, validate_default=True, alias="postCategory", description="岗位类别编码")
    post_sort: int | None = Field(default=None, validate_default=True, alias="postSort", description="显示顺序")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")
    remark: str | None = Field(default=None, description="备注")

    @field_validator("dept_id")
    @classmethod
    def check_dept_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("部门id不能为空")
        return value

    @field_validator("post_code")
    @classmethod
    def check_post_code(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("岗位编码不能为空")
        if len(value) > 64:
            raise ValueError("岗位编码长度不能超过64个字符")
        return value

    @field_validator("post_name")
    @classmethod
    def check_post_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("岗位名称不能为空")
        if len(value) > 50:
            raise ValueError("岗位名称长度不能超过50个字符")
        return value

    @field_validator("post_category")
    @classmethod
    def check_post_category(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 100:
            raise ValueError("类别编码长度不能超过100个字符")
        return value

    @field_validator("post_sort")
    @classmethod
    def check_post_sort(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("显示顺序不能为空")
        return value


class PostUpdateSchema(PostCreateSchema):
    """修改岗位入参。"""

    id: int | None = Field(default=None, validate_default=True, description="岗位ID")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("岗位ID不能为空")
        return value


class PostOutSchema(BaseModel):
    """岗位出参（另含部门名翻译 deptName）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)

    id: int | None = Field(default=None, description="岗位ID")
    dept_id: int | None = Field(default=None, description="部门id")
    post_code: str | None = Field(default=None, description="岗位编码")
    post_name: str | None = Field(default=None, description="岗位名称")
    post_category: str | None = Field(default=None, description="岗位类别编码")
    post_sort: int | None = Field(default=None, description="显示顺序")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")
    remark: str | None = Field(default=None, description="备注")
    create_time: DateTimeStr | None = Field(default=None, description="创建时间")
    dept_name: str | None = Field(default=None, description="部门名")


class PostInfoSchema(BaseModel):
    """岗位精简信息（供用户等模块关联使用）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)

    id: int | None = Field(default=None, description="岗位ID")
    dept_id: int | None = Field(default=None, description="部门id")
    post_code: str | None = Field(default=None, description="岗位编码")
    post_name: str | None = Field(default=None, description="岗位名称")
    post_category: str | None = Field(default=None, description="岗位类别编码")
