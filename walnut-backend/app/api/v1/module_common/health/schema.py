from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    status: int = Field(default=0, description="依赖状态 1=正常 0=异常")
    latency_ms: float | None = Field(default=None, description="探测耗时(毫秒)")


class HealthOut(BaseModel):
    status: int = Field(default=1, description="进程状态")
    timestamp: str = Field(default="", description="时间戳")
    version: str = Field(default="", description="版本号")
    uptime_seconds: float = Field(default=0.0, description="运行时长(秒)")


class ReadinessOut(HealthOut):
    dependencies: dict[str, DependencyStatus] = Field(default_factory=dict, description="依赖状态")
    disk_usage: float = Field(default=-1.0, description="磁盘使用率(%)")
