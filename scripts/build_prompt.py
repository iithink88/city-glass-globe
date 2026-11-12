#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把城市名转换成「城市装进玻璃球」海报的生图提示词（纯标准库，无第三方依赖）。

示例：
  python build_prompt.py 桂林 --outdir out/guilin
  python build_prompt.py 北京 上海 西安 --outdir out/batch --style night
  python build_prompt.py 保定 --landmarks "直隶总督署,古莲花池,大慈阁,驴肉火烧摊" --outdir out/baoding
  python build_prompt.py 任意小城 --outdir out/xiaocheng

输出（每个城市）：
  <outdir>/<城市>_prompt.txt     主提示词（默认中文）
  <outdir>/<城市>_prompt_en.txt  英文提示词（备用）
  <outdir>/<城市>_meta.json      后期叠加中文排版所需的字段
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "references" / "cities.json"

STYLE_EXTRA_ZH = {
    "poster": "",
    "snow": "整体为冬日雪花玻璃球氛围：球内飘着细密雪粒，屋顶与树枝覆雪，行人呼出白气，灯光更暖更浓；",
    "night": "整体为夜景模式：球内万家灯火、橱窗透亮但招牌不留字，深蓝夜空与暖黄灯光对比，玻璃球向外透出柔和光晕；",
    "ink": "整体转为国风淡彩：低饱和青绿与赭石，宣纸般细腻肌理，山峦留白，微缩景观带一点工笔界画味道，仍保留玻璃与木底座的写实质感；",
    "clean": "整体为极简棚拍：纯色暖灰背景，去掉花枝前景，只留柔和顶光与一道干净投影，画面更克制；",
}

STYLE_EXTRA_EN = {
    "poster": "",
    "snow": "Winter snow-globe mood: fine drifting snow inside, snow-capped roofs and branches, warm glowing windows;",
    "night": "Night version: thousands of tiny warm lights inside, deep blue sky, soft glow radiating from the globe, signs glowing but blank;",
    "ink": "Oriental ink-and-wash tint: muted celadon and ochre, fine paper texture, elegant negative space, still photoreal glass and wood;",
    "clean": "Minimal studio version: plain warm grey backdrop, no floral foreground, one soft top light and a single clean shadow;",
}


def load_db() -> dict:
    with DB_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_city(name: str, db: dict):
    """支持中文名、英文名、别名与包含匹配。"""
    if name in db and not name.startswith("_"):
        return name, db[name]
    low = name.strip().lower()
    for key, item in db.items():
        if key.startswith("_"):
            continue
        names = [key, item.get("en", "")] + list(item.get("aliases", []))
        if any(low == str(n).lower() for n in names):
            return key, item
    for key, item in db.items():
        if key.startswith("_"):
            continue
        if low and (low in key.lower() or key.lower() in low or low in str(item.get("en", "")).lower()):
            return key, item
    return name, None


def split_list(text: str) -> list:
    parts = [p.strip() for p in text.replace("，", ",").replace("、", ",").split(",") if p.strip()]
    return parts


def make_item(city: str, hit: dict | None, args) -> dict:
    base = dict(hit) if hit else {}
    is_new = hit is None
    if is_new:
        base = {
            "en": city,
            "coords": "",
            "landmarks": [
                f"{city}最具辨识度的地标建筑",
                f"{city}老城街巷与市井生活",
                "当地河流、山体或海岸等自然地貌",
                "街边小吃摊、树木与三三两两的行人",
            ],
            "scene": f"以{city}的真实城市气质为蓝本，远景天际线与近景街市自然衔接，不虚构不存在的著名建筑",
            "season": "晴朗柔和的日光",
            "palette": "温润的暖米色与城市本色",
            "slogan": f"把{city}，装进一颗球里。",
        }
    if args.landmarks:
        base["landmarks"] = split_list(args.landmarks)
    if args.scene:
        base["scene"] = args.scene
    if args.season:
        base["season"] = args.season
    if args.palette:
        base["palette"] = args.palette
    if args.english:
        base["en"] = args.english
    if args.coords:
        base["coords"] = args.coords
    if args.slogan:
        base["slogan"] = args.slogan
    base["_new"] = is_new
    return base


def title_lines(city: str, custom: str | None) -> list:
    if custom:
        return split_list(custom) or [custom]
    head = "如果把" + city
    if len(head) <= 7:
        return [head, "装进玻璃球"]
    return ["如果把", city, "装进玻璃球"]


def build_zh(city: str, c: dict, args) -> str:
    marks = "、".join(c["landmarks"])
    style = STYLE_EXTRA_ZH.get(args.style, "")
    extra = ("额外要求：" + args.extra + "。") if args.extra else ""
    return f"""竖版 3:4 商业海报摄影：一件摆放在暖米色亚麻布桌面上的「{city}」主题透明玻璃球微缩城市纪念品。

【主体】一只完整、圆润、比例真实的透明水晶玻璃球，占据画面高度约 70%，居中；玻璃有清晰厚度、真实折射与边缘高光，表面映出柔和窗格光，通透、无气泡、无杂质、不变形。球下方是深胡桃木抛光圆形底座，木纹细腻，底座正面嵌一块空白金色铭牌（不要刻字）；球体与底座衔接自然，桌面有柔和投影。

【球内微缩世界】超精细微缩模型风格的 {city} 全景：{marks}；{c['scene']}。前景是尺度极小的行人、街边小吃摊、树木与石板路，中景是街巷与水岸，远景是天空和地平线；层次分明，tilt-shift 移轴景深，微缩模型质感与写实摄影质感融合，细节丰富但不拥挤，能一眼认出这是 {city}。

【光线与季节】{c['season']}，{c['palette']}；球内透出暖黄色灯火，球体外侧是柔和的自然侧逆光，光比克制、氛围温润。{style}

【背景与构图】暖米色／浅杏色纯色背景，右上角有一枝虚化的梅花或玉兰作前景点缀，浅景深柔焦；左上角与画面底部各留出大片干净留白，供后期叠加标题文字。居中对称构图，平视略俯，产品摄影级布光，8K 超写实，Octane render 质感，色彩高级，文创纪念品广告大片。{extra}

【必须遵守】画面中不出现任何文字、字母、数字、招牌字、铭牌字、水印、logo、二维码；店铺招牌与金色铭牌保持空白；不出现人手、卡通人物、第二只球体、破碎或变形的玻璃、鱼眼畸变；只出现一个完整玻璃球与一个木底座，球体不裁切。""".strip()


def build_en(city: str, c: dict, args) -> str:
    marks = ", ".join(c["landmarks"])
    style = STYLE_EXTRA_EN.get(args.style, "")
    extra = ("Extra requirement: " + args.extra + ". ") if args.extra else ""
    return f"""Vertical 3:4 commercial poster photograph of a collectible transparent glass snow-globe containing a miniature city of {c['en']} ({city}), resting on a warm beige linen tabletop.

[Object] One complete, perfectly round, realistically proportioned crystal glass globe occupying about 70% of the frame height, centered; visible glass thickness, true refraction, crisp rim highlights, soft window reflections, perfectly clear with no bubbles or distortion. Below it, a polished dark walnut round wooden base with fine grain and a BLANK brass nameplate (no engraving). Natural contact shadow on the table.

[World inside] Ultra-detailed miniature model of {c['en']}: {marks}; {c['scene']}. Tiny pedestrians, street food stalls, trees and cobblestones in the foreground, lanes and waterfront mid-ground, sky and skyline far behind; clear depth layers, tilt-shift depth of field, blend of miniature-model craft and photoreal photography, rich but uncluttered, unmistakably {c['en']}.

[Light and mood] {c['season']}, palette of {c['palette']}; warm yellow light glowing from inside the globe, soft natural rim light outside, gentle contrast. {style}

[Background and composition] Plain warm beige / light apricot backdrop, a blurred branch of plum or magnolia blossom in the upper right foreground, shallow depth of field; large clean empty areas at the upper left and along the bottom reserved for later typography. Centered symmetrical composition, eye-level slightly above, product-photography lighting, 8K photoreal, Octane render finish, refined color grading, premium souvenir advertising campaign. {extra}

[Strict rules] No text, letters, numbers, signage lettering, engraved lettering, watermark, logo or QR code anywhere; all shop signs and the brass plate stay blank. No human hands, no cartoon figures, no second globe, no cracked or warped glass, no fisheye distortion. Exactly one complete uncropped glass globe on one wooden base.""".strip()


def main() -> int:
    p = argparse.ArgumentParser(description="城市玻璃球海报提示词生成器")
    p.add_argument("cities", nargs="+", help="一个或多个城市名")
    p.add_argument("--outdir", default=".", help="输出目录")
    p.add_argument("--lang", choices=["zh", "en"], default="zh", help="主提示词语言")
    p.add_argument("--style", choices=list(STYLE_EXTRA_ZH), default="poster", help="风格变体")
    p.add_argument("--landmarks", default="", help="覆盖地标，逗号分隔")
    p.add_argument("--scene", default="", help="覆盖场景描述")
    p.add_argument("--season", default="", help="覆盖季节/光线")
    p.add_argument("--palette", default="", help="覆盖色调")
    p.add_argument("--english", default="", help="覆盖英文名")
    p.add_argument("--coords", default="", help="覆盖经纬度")
    p.add_argument("--slogan", default="", help="覆盖海报短句")
    p.add_argument("--title", default="", help="覆盖标题，用逗号表示换行")
    p.add_argument("--signature", default="@你的名字", help="左下角署名")
    p.add_argument("--extra", default="", help="追加自定义要求")
    args = p.parse_args()

    db = load_db()
    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    written = []

    for city in args.cities:
        key, hit = find_city(city, db)
        city_name = key
        c = make_item(city_name, hit, args)
        zh, en = build_zh(city_name, c, args), build_en(city_name, c, args)
        primary = zh if args.lang == "zh" else en

        f_zh = outdir / f"{city_name}_prompt.txt"
        f_en = outdir / f"{city_name}_prompt_en.txt"
        f_meta = outdir / f"{city_name}_meta.json"
        f_zh.write_text(zh, encoding="utf-8")
        f_en.write_text(en, encoding="utf-8")

        meta = {
            "city": city_name,
            "english": c.get("en", ""),
            "coords": c.get("coords", ""),
            "title_lines": title_lines(city_name, args.title or None),
            "slogan": c.get("slogan", ""),
            "signature": args.signature,
            "landmarks": c["landmarks"],
            "season": c.get("season", ""),
            "palette": c.get("palette", ""),
            "style": args.style,
            "is_new_city": c.get("_new", False),
            "prompt_zh": zh,
            "prompt_en": en,
        }
        f_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append((city_name, f_zh if args.lang == "zh" else f_en, f_meta, primary))

        if c.get("_new"):
            print(f"[提示] 「{city_name}」不在城市素材库中，已使用通用地标模板。若要更精准，"
                  f"用 --landmarks 指定，或把该城市补进 {DB_PATH}", file=sys.stderr)

    if len(written) == 1:
        city_name, f_main, f_meta, primary = written[0]
        print(primary)
        print("\n" + "=" * 60)
        print(f"主提示词文件: {f_main}")
        print(f"英文提示词:   {f_main.parent / (city_name + '_prompt_en.txt')}")
        print(f"排版元数据:   {f_meta}")
    else:
        print(f"已为 {len(written)} 座城市生成提示词，目录: {outdir}")
        for city_name, f_main, f_meta, _ in written:
            print(f"  {city_name}: {f_main.name} / {f_meta.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
