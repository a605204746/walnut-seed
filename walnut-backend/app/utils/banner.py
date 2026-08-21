from app.config.path_conf import BANNER_FILE

_FALLBACK = r"""
 __        __   _     _             _   ____                 _
 \ \      / /_ | |   | |_ __  _   _| |_| __ )  ___  ___   __| |
  \ \ /\ / / _ \| |   | | '_ \| | | | __|  _ \ / _ \/ _ \ / _` |
   \ V  V / (_) | |___| | | | | |_| | |_| |_) |  __/  __/| (_| |
    \_/\_/ \___/|_____|_|_| |_|\__,_|\__|____/ \___|\___(_)__,_|
"""


def worship() -> str:
    """读取启动 banner 文本。"""
    try:
        if BANNER_FILE.exists():
            return BANNER_FILE.read_text(encoding="utf-8")
    except Exception:
        pass
    return _FALLBACK
