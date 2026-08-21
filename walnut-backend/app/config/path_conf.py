from pathlib import Path

# 后端根目录（walnut-backend/）
BASE_DIR = Path(__file__).parent.parent.parent

# 仓库根目录（walnut-backend/ 的上一级）
ROOT_DIR = BASE_DIR.parent

# 运行时数据统一存放目录（仓库根目录 data/：日志 / 上传）
DATA_DIR = ROOT_DIR / "data"

# alembic 迁移文件存放路径
ALEMBIC_VERSION_DIR = BASE_DIR / "app" / "alembic" / "versions"

# 日志文件路径
LOG_DIR = DATA_DIR / "logs"

# 本地文件存储（上传）目录
UPLOAD_DIR = DATA_DIR / "upload"

# 静态资源目录
STATIC_DIR = BASE_DIR / "static"

# 环境配置目录
ENV_DIR = BASE_DIR / "env"

# 初始化脚本 SQL 目录
SCRIPT_DIR: Path = BASE_DIR / "app" / "seed" / "sql"

# 模版文件目录（预留代码生成）
TEMPLATE_DIR: Path = BASE_DIR / "templates"

# 前端构建输出目录
FRONTEND_DIST_DIR: Path = BASE_DIR / "dist"

# banner.txt 文件路径
BANNER_FILE = BASE_DIR / "banner.txt"

# 国际化资源目录
I18N_DIR = BASE_DIR / "app" / "i18n"
