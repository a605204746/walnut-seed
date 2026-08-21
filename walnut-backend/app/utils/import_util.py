"""模型自动发现工具（供 alembic autogenerate 使用）。"""

import importlib
from pathlib import Path

# app/ 包目录
_APP_DIR = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _APP_DIR.parent


class ImportUtil:
    @staticmethod
    def find_models(base) -> list:
        """导入所有 ``**/model.py`` 模块并收集 ``base`` 的具体子类。"""
        # 导入全部 model 模块，触发 ORM 注册
        for path in sorted(_APP_DIR.rglob("model.py")):
            rel = path.relative_to(_PROJECT_ROOT).with_suffix("")
            module_name = ".".join(rel.parts)
            try:
                importlib.import_module(module_name)
            except Exception as e:  # pragma: no cover
                print(f"[alembic] 导入模型模块失败 {module_name}: {e}")

        # 递归收集具体子类
        found: list = []

        def _collect(cls):
            for sub in cls.__subclasses__():
                # __abstract__ 会经 MRO 继承，须以类自身声明为准（自身未声明即具体模型）
                if "__abstract__" not in sub.__dict__ and sub not in found:
                    found.append(sub)
                _collect(sub)

        _collect(base)
        return found
