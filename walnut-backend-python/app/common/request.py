"""分页请求模型。"""

from pydantic import BaseModel, ConfigDict, Field


class PageReq(BaseModel):
    """分页请求基类。

    - ``page_num`` 默认 1；
    - ``page_size`` 默认 None 表示“查询全部”；
    - ``order_by_column`` / ``is_asc`` 支持逗号分隔的多字段排序。

    前端契约字段名为驼峰（pageNum/pageSize/orderByColumn/isAsc），通过 alias 对齐。
    """

    model_config = ConfigDict(populate_by_name=True)

    page_num: int = Field(default=1, ge=1, alias="pageNum", description="页码")
    page_size: int | None = Field(default=None, ge=1, alias="pageSize", description="每页数量，None 表示查询全部")
    order_by_column: str | None = Field(default=None, alias="orderByColumn", description="排序列（逗号分隔）")
    is_asc: str | None = Field(default=None, alias="isAsc", description="排序方向 asc/desc（逗号分隔）")

    @property
    def offset(self) -> int:
        return (self.page_num - 1) * (self.page_size or 0)

    def has_limit(self) -> bool:
        return self.page_size is not None
