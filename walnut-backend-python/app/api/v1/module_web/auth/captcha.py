"""图形验证码生成（Pillow 实现）。

- math 模式：生成形如 ``3+5=?`` 的算式，返回 (算式, 答案)；
- char 模式：生成 4 位字母数字随机串，返回 (随机串, 随机串)。
图片为 160x60 PNG（base64 不带 data URI 前缀，前端自行拼接）。
"""

import base64
import io
import random
import string

from PIL import Image, ImageDraw, ImageFont

_WIDTH, _HEIGHT = 160, 60
_BG_RANGE = (230, 250)
_TEXT_COLORS = [(25, 90, 180), (180, 40, 40), (30, 140, 60), (120, 60, 170), (200, 110, 20)]


def _load_font(size: int = 40) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans-Bold.ttf", "msyhbd.ttc", "simhei.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # 极老版本 Pillow 兜底
        return ImageFont.load_default()


def _draw_noise(draw: ImageDraw.ImageDraw) -> None:
    """干扰线 + 干扰圈。"""
    for _ in range(4):
        x1, y1 = random.randint(0, _WIDTH), random.randint(0, _HEIGHT)
        x2, y2 = random.randint(0, _WIDTH), random.randint(0, _HEIGHT)
        draw.line((x1, y1, x2, y2), fill=_TEXT_COLORS[random.randint(0, len(_TEXT_COLORS) - 1)], width=1)
    for _ in range(3):
        x, y = random.randint(0, _WIDTH - 20), random.randint(0, _HEIGHT - 20)
        r = random.randint(5, 12)
        draw.ellipse((x, y, x + 2 * r, y + 2 * r), outline=_TEXT_COLORS[random.randint(0, len(_TEXT_COLORS) - 1)])


def _render(text: str) -> str:
    """渲染文本为 PNG base64（不带 data URI 前缀）。"""
    bg_color = tuple(random.randint(_BG_RANGE[0], _BG_RANGE[1]) for _ in range(3))
    image = Image.new("RGB", (_WIDTH, _HEIGHT), bg_color)
    draw = ImageDraw.Draw(image)
    _draw_noise(draw)

    font = _load_font(40)
    offset = 12
    for ch in text:
        color = _TEXT_COLORS[random.randint(0, len(_TEXT_COLORS) - 1)]
        draw.text((offset, random.randint(2, 12)), ch, font=font, fill=color)
        offset += (_WIDTH - 24) // max(len(text), 1)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def generate_math(number_length: int = 1) -> tuple[str, str, str]:
    """数学算式验证码。

    返回 (展示文本如 ``3+5=?``, 答案, base64 图片)。
    """
    bound = 10**max(number_length, 1)
    a = random.randint(0, bound - 1)
    b = random.randint(0, bound - 1)
    if random.random() < 0.5:
        text, answer = f"{a}+{b}=?", str(a + b)
    else:
        if a < b:
            a, b = b, a
        text, answer = f"{a}-{b}=?", str(a - b)
    return text, answer, _render(text)


def generate_char(char_length: int = 4) -> tuple[str, str, str]:
    """字符验证码。返回 (随机串, 随机串, base64 图片)。"""
    chars = string.ascii_letters + string.digits
    code = "".join(random.choice(chars) for _ in range(max(char_length, 1)))
    return code, code, _render(code)
