#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在生成的玻璃球图片上叠加中文海报排版（标题／英文名／经纬度／短句／署名）。

图像模型生成中文容易乱码，所以生图阶段一律要求「画面无文字」，文字由本脚本用系统字体绘制，
保证 100% 正确、可改、可脱敏。依赖 Pillow。

示例：
  python add_text_overlay.py 桂林.png --meta out/guilin/桂林_meta.json --out out/guilin/桂林_海报.png
  python add_text_overlay.py 保定.png --city 保定 --panel --scale 0.92
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("缺少 Pillow。请用 WorkBuddy 托管 Python 运行，或先安装 pillow。", file=sys.stderr)
    raise SystemExit(2)

INK = (74, 46, 27)          # 深棕，主标题
INK_SOFT = (107, 78, 54)    # 浅棕，副信息
PAPER = (250, 241, 226)     # 米色描边/底衬

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\STZHONGS.TTF",
    r"C:\Windows\Fonts\STSONG.TTF",
    r"C:\Windows\Fonts\simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]


def find_font(explicit: str | None = None) -> str:
    if explicit:
        if not Path(explicit).is_file():
            raise SystemExit(f"字体文件不存在: {explicit}")
        return explicit
    windir = os.environ.get("WINDIR", r"C:\Windows")
    candidates = [p.replace(r"C:\Windows", windir) for p in FONT_CANDIDATES]
    for p in candidates:
        if Path(p).is_file():
            return p
    raise SystemExit("未找到中文字体。请用 --font 指定一个 .ttf/.ttc 中文字体文件路径。")


def font(path: str, size: int):
    return ImageFont.truetype(path, max(8, int(size)))


def text(draw, xy, content, f, fill, anchor=None, stroke=0):
    kwargs = {}
    if anchor:
        kwargs["anchor"] = anchor
    if stroke:
        kwargs["stroke_width"] = stroke
        kwargs["stroke_fill"] = (*PAPER, 190)
    try:
        draw.text(xy, content, font=f, fill=fill, **kwargs)
    except TypeError:
        kwargs.pop("stroke_width", None)
        kwargs.pop("stroke_fill", None)
        draw.text(xy, content, font=f, fill=fill, **kwargs)


def wrap_slogan(s: str, width: int = 13, max_lines: int = 3):
    seps = "，。、；：！？,.!?"
    buf, lines = "", []
    for ch in s.strip():
        buf += ch
        if ch in seps or len(buf) >= width:
            if buf.strip():
                lines.append(buf.strip())
            buf = ""
    if buf.strip():
        lines.append(buf.strip())
    return lines[:max_lines]


def load_meta(args) -> dict:
    if args.meta:
        p = Path(args.meta)
    elif args.city:
        p = Path(args.image).parent / f"{args.city}_meta.json"
    else:
        cands = sorted(Path(args.image).parent.glob("*_meta.json"))
        if len(cands) == 1:
            p = cands[0]
        else:
            raise SystemExit("请用 --meta 指定元数据文件，或用 --city 指定城市名。")
    if not p.is_file():
        raise SystemExit(f"找不到元数据文件: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description="玻璃球海报中文排版叠加")
    p.add_argument("image", help="生图得到的图片路径")
    p.add_argument("--meta", default="", help="build_prompt.py 产出的 *_meta.json")
    p.add_argument("--city", default="", help="未指定 --meta 时，用城市名找同目录 <城市>_meta.json")
    p.add_argument("--out", default="", help="输出路径，默认 <原名>_海报.png")
    p.add_argument("--font", default="", help="指定中文字体文件")
    p.add_argument("--scale", type=float, default=1.0, help="文字整体缩放，默认 1.0")
    p.add_argument("--panel", action="store_true", help="在文字区加半透明米色底衬（背景杂乱时启用）")
    p.add_argument("--hide-watermark", action="store_true", help="裁掉底部 6%（等效 --crop-bottom 0.06），无痕去掉右下角平台水印")
    p.add_argument("--crop-bottom", type=float, default=0.0, help="裁掉底部比例 0~0.2，自定义去水印幅度")
    p.add_argument("--signature", default="", help="覆盖左下角署名；传空格可留空")
    p.add_argument("--slogan", default="", help="覆盖右下角短句")
    args = p.parse_args()

    src = Path(args.image).expanduser().resolve()
    if not src.is_file():
        raise SystemExit(f"图片不存在: {src}")
    meta = load_meta(args)
    font_path = find_font(args.font or None)

    img = Image.open(src).convert("RGBA")

    # 平台常在右下角叠加「AI生成」水印。底部本来就是桌布留白，裁掉一小条既无痕，
    # 又让画幅从 2:3 更接近参考海报的 3:4。
    crop_ratio = args.crop_bottom
    if args.hide_watermark and crop_ratio <= 0:
        crop_ratio = 0.06
    if 0 < crop_ratio < 0.2:
        img = img.crop((0, 0, img.width, int(img.height * (1 - crop_ratio))))

    W, H = img.size
    s = (W / 1080.0) * args.scale
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    title_lines = meta.get("title_lines") or ["如果把" + meta.get("city", ""), "装进玻璃球"]
    signature = args.signature if args.signature != "" else meta.get("signature", "@你的名字")
    slogan = args.slogan or meta.get("slogan", "")

    # 可选底衬：左上标题区 + 底部信息条
    if args.panel:
        d.rectangle([0, 0, int(W * 0.60), int(H * 0.26)], fill=(*PAPER, 105))
        d.rectangle([0, int(H * 0.87), W, H], fill=(*PAPER, 105))

    # 左上：主标题
    fs_title = (68 if len(title_lines) > 2 else 76) * s
    x = int(W * 0.075)
    y = int(H * 0.045)
    lh = fs_title * 1.24
    f_title = font(font_path, fs_title)
    for line in title_lines:
        text(d, (x, y), line, f_title, INK, stroke=max(1, int(2 * s)))
        y += lh

    # 标题下细线
    y += 0.010 * H
    d.line([(x, y), (x + 0.085 * W, y)], fill=INK_SOFT, width=max(1, int(2 * s)))
    y += 0.016 * H

    # 英文名 + 经纬度
    f_en = font(font_path, 27 * s)
    f_coord = font(font_path, 21 * s)
    if meta.get("english"):
        text(d, (x, y), meta["english"], f_en, INK_SOFT, stroke=max(1, int(1 * s)))
        y += 0.032 * H
    if meta.get("coords"):
        text(d, (x, y), meta["coords"], f_coord, INK_SOFT, stroke=max(1, int(1 * s)))

    # 左下：署名
    f_sign = font(font_path, 30 * s)
    if signature.strip():
        text(d, (x, int(H * 0.925)), signature, f_sign, INK_SOFT, stroke=max(1, int(1 * s)))

    # 右下：短句（右对齐，向上堆叠）
    if slogan:
        fs_slogan = 28 * s
        f_slogan = font(font_path, fs_slogan)
        lines = wrap_slogan(slogan)
        right = int(W * 0.925)
        bottom = int(H * 0.895)  # 上移，避开右下角平台水印
        line_h = fs_slogan * 1.36
        for i, line in enumerate(lines):
            yy = bottom - line_h * (len(lines) - i)
            box = f_slogan.getbbox(line)
            tw = box[2] - box[0]
            text(d, (right - tw, yy), line, f_slogan, INK, stroke=max(1, int(1 * s)))

    out = Image.alpha_composite(img, layer).convert("RGB")
    dest = Path(args.out).expanduser().resolve() if args.out else src.with_name(src.stem + "_海报.png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, "PNG")
    print(f"已生成海报: {dest}  ({W}x{H})  字体: {Path(font_path).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
