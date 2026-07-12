"""生成 PWA icon：破曉深藍底 + 銅鐘 + 晨光。

用法：python scripts/make_icons.py
輸出：static/icons/ 下的各尺寸 PNG。
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "static" / "icons"

NAVY_TOP = (22, 36, 58)      # 天將亮的深藍
NAVY_BOTTOM = (42, 63, 97)   # 地平線附近微亮
BRASS = (222, 168, 62)       # 銅鐘
BRASS_DARK = (176, 126, 38)  # 鐘的暗部
GLOW = (255, 214, 130)       # 晨光


def draw_icon(size: int = 1024) -> Image.Image:
    s = size / 1024  # 所有座標以 1024 畫布為基準
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)

    # 背景：由上而下的破曉漸層
    for y in range(size):
        t = y / size
        color = tuple(int(a + (b - a) * t) for a, b in zip(NAVY_TOP, NAVY_BOTTOM))
        d.line([(0, y), (size, y)], fill=color)

    # 鐘背後的晨光暈（同心圓，越外越淡）
    cx, cy = 512 * s, 470 * s
    for r, alpha in [(430, 26), (360, 36), (290, 48)]:
        overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([cx - r * s, cy - r * s, cx + r * s, cy + r * s],
                   fill=GLOW + (alpha,))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)

    # 鐘體：圓頂 + 微張的鐘身 + 鐘唇
    d.pieslice([332 * s, 232 * s, 692 * s, 592 * s], 180, 360, fill=BRASS)  # 圓頂
    d.polygon([
        (332 * s, 410 * s), (300 * s, 620 * s),
        (724 * s, 620 * s), (692 * s, 410 * s),
    ], fill=BRASS)                                                          # 鐘身
    d.rounded_rectangle([272 * s, 616 * s, 752 * s, 672 * s],
                        radius=28 * s, fill=BRASS_DARK)                     # 鐘唇
    d.rounded_rectangle([482 * s, 180 * s, 542 * s, 250 * s],
                        radius=24 * s, fill=BRASS_DARK)                     # 頂鈕

    # 鐘舌
    d.ellipse([472 * s, 690 * s, 552 * s, 770 * s], fill=GLOW)

    # 左右兩道晨響（聲波弧線）
    w = int(30 * s)
    d.arc([120 * s, 320 * s, 400 * s, 720 * s], 130, 210, fill=GLOW, width=w)
    d.arc([624 * s, 320 * s, 904 * s, 720 * s], -30, 50, fill=GLOW, width=w)

    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    master = draw_icon(1024)
    for name, px in [
        ("icon-512.png", 512), ("icon-192.png", 192),
        ("apple-touch-icon.png", 180), ("favicon-32.png", 32),
    ]:
        master.resize((px, px), Image.LANCZOS).save(OUT / name)
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
