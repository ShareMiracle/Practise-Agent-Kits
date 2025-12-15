#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
xhs_publisher.py

功能：
- 根据命令行参数，选择某一年（2021–2025）或 "trend"（整体趋势），
  自动从 llm_reports + figs 目录里挑选对应的小红书图文素材。
- 或者使用 --all 一次性把所有年份 & 趋势的素材包都打好，
  生成到 xhs_exports/ 下，并写一份 INDEX.md 索引方便挑选。

用法示例：

  # 2021 年，第 1 条年终文案
  python xhs_publisher.py --topic 2021 --variant 1

  # 2023 年，第 2 条年终文案
  python xhs_publisher.py --topic 2023 --variant 2

  # 整体趋势 + 2026 预测（只有 1 条，不需要 variant）
  python xhs_publisher.py --topic trend

  # 一口气把所有素材包都打好（2021–2025 每年多条 + trend）
  python xhs_publisher.py --all

生成结果示例：
  xhs_exports/
    2021_v1/
      note_title.txt
      note_body.txt
      img_01.png
      ...
    2021_v2/
      ...
    2022_v1/
      ...
    ...
    trend/
      note_title.txt
      note_body.txt
      img_01.png
      ...
    INDEX.md   # 所有素材包的简要列表
"""

import os
import argparse
import shutil
from dataclasses import dataclass
from typing import List, Tuple


# -------- 路径配置（默认认为脚本和 figs/ llm_reports 在同一根目录下） --------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE_DIR, "llm_reports")
FIGS_DIR = os.path.join(BASE_DIR, "figs")
EXPORT_ROOT = os.path.join(BASE_DIR, "xhs_exports")


@dataclass
class XHSNote:
    """一条准备发到小红书的笔记."""
    slug: str               # 例如 "2021_v1" 或 "trend"
    title: str              # 标题（建议放小红书标题栏）
    body: str               # 正文（整段文案）
    image_paths: List[str]  # 按顺序推荐的图片路径（不超过 9 张）


# -------- 工具函数 --------

def _split_markdown_by_dash(text: str) -> List[str]:
    """
    把 year_XXXX_summary.md 用 '---' 分成多段。
    如果文件里没有 '---'，就当成只有一段。
    """
    lines = text.splitlines()
    parts: List[List[str]] = []
    buf: List[str] = []

    for line in lines:
        if line.strip() == "---":
            if buf:
                parts.append(buf)
                buf = []
        else:
            buf.append(line)

    if buf:
        parts.append(buf)

    if not parts:
        return [text.strip()]

    return ["\n".join(chunk).strip() for chunk in parts if "".join(chunk).strip()]


def _extract_title_and_body(block: str, fallback_title: str) -> Tuple[str, str]:
    """
    默认把第一行非空行当成标题，剩下的作为正文。
    如果整个 block 为空，就用 fallback_title 当标题。
    """
    lines = [ln for ln in block.splitlines()]
    non_empty = [ln for ln in lines if ln.strip()]

    if not non_empty:
        return fallback_title, ""

    title = non_empty[0].strip()
    # 正文从标题下一行开始
    body_lines = lines[lines.index(non_empty[0]) + 1:]
    body = "\n".join(body_lines).lstrip()
    # 对小红书而言，正文直接用完整 block 更自然，这里 body 用完整 block
    return title, block.strip()


def _add_if_exists(paths: List[str], path: str) -> None:
    """如果文件存在，就 append 到 paths 里。"""
    if os.path.exists(path):
        paths.append(path)
    else:
        print(f"[WARN] 图片不存在，跳过: {path}")


# -------- 加载文案：单条 --------

def load_year_note(year: int, variant: int = 1) -> XHSNote:
    """
    加载某一年（2021–2025）的第 variant 条文案，并组合推荐图片。
    variant = 1 或 2（因为每年我们生成了两条文案）。
    """
    if variant < 1:
        raise ValueError("variant 不能小于 1")

    md_path = os.path.join(REPORT_DIR, f"year_{year}_summary.md")
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"找不到年度文案文件: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    blocks = _split_markdown_by_dash(text)
    if variant > len(blocks):
        raise ValueError(
            f"{year} 年实际只有 {len(blocks)} 段文案，"
            f"variant={variant} 超出范围。"
        )

    chosen_block = blocks[variant - 1]
    fallback_title = f"{year} 年 AI 顶会趋势复盘"
    title, body = _extract_title_and_body(chosen_block, fallback_title)

    images: List[str] = []
    _add_if_exists(images, os.path.join(FIGS_DIR, "cover_image.png"))
    _add_if_exists(
        images,
        os.path.join(FIGS_DIR, "year_bars", f"year_{year}_top_categories.png"),
    )
    _add_if_exists(
        images,
        os.path.join(FIGS_DIR, "trends", "trend_focus_multi_lines.png"),
    )
    _add_if_exists(
        images,
        os.path.join(FIGS_DIR, "stacked_share", "category_share_2021_2025.png"),
    )

    slug = f"{year}_v{variant}"
    return XHSNote(slug=slug, title=title, body=body, image_paths=images)


def load_trend_note() -> XHSNote:
    """
    加载 2021–2025 总趋势 + 2026 预测的文案，并组合推荐图片。
    """
    md_path = os.path.join(REPORT_DIR, "trend_2021_2025_and_forecast.md")
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"找不到趋势文案文件: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    fallback_title = "2021–2025 顶会趋势一图看完 + 2026 预测"
    title, body = _extract_title_and_body(text, fallback_title)

    images: List[str] = []
    _add_if_exists(images, os.path.join(FIGS_DIR, "cover_image.png"))
    _add_if_exists(
        images,
        os.path.join(FIGS_DIR, "trends", "trend_focus_multi_lines.png"),
    )
    _add_if_exists(
        images,
        os.path.join(FIGS_DIR, "stacked_share", "category_share_2021_2025.png"),
    )
    _add_if_exists(
        images,
        os.path.join(FIGS_DIR, "category_leaderboards", "top_total_categories.png"),
    )
    _add_if_exists(
        images,
        os.path.join(FIGS_DIR, "category_leaderboards", "top_growth_categories.png"),
    )
    _add_if_exists(
        images,
        os.path.join(FIGS_DIR, "conf_category", "conf_category_heatmap.png"),
    )
    _add_if_exists(
        images,
        os.path.join(FIGS_DIR, "conf_category", "conf_category_bubble.png"),
    )

    images = images[:9]
    return XHSNote(slug="trend", title=title, body=body, image_paths=images)


# -------- 加载文案：某一年的所有变体（给 --all 用） --------

def load_all_year_notes(year: int) -> List[XHSNote]:
    """
    加载某一年的所有段落文案（通常 2 段），每一段做成一条笔记。
    """
    md_path = os.path.join(REPORT_DIR, f"year_{year}_summary.md")
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"找不到年度文案文件: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    blocks = _split_markdown_by_dash(text)
    if not blocks:
        return []

    notes: List[XHSNote] = []
    for variant, block in enumerate(blocks, start=1):
        fallback_title = f"{year} 年 AI 顶会趋势复盘（版本 {variant}）"
        title, body = _extract_title_and_body(block, fallback_title)

        images: List[str] = []
        _add_if_exists(images, os.path.join(FIGS_DIR, "cover_image.png"))
        _add_if_exists(
            images,
            os.path.join(FIGS_DIR, "year_bars", f"year_{year}_top_categories.png"),
        )
        _add_if_exists(
            images,
            os.path.join(FIGS_DIR, "trends", "trend_focus_multi_lines.png"),
        )
        _add_if_exists(
            images,
            os.path.join(FIGS_DIR, "stacked_share", "category_share_2021_2025.png"),
        )

        slug = f"{year}_v{variant}"
        notes.append(XHSNote(slug=slug, title=title, body=body, image_paths=images))

    return notes


# -------- 导出到本地目录，方便手动发小红书 --------

def export_note(note: XHSNote) -> str:
    """
    把文案和图片导出到一个独立目录，返回该目录路径。
    目录结构：
        <EXPORT_ROOT>/<slug>/
            note_title.txt
            note_body.txt
            img_01.png
            img_02.png
            ...
    """
    out_dir = os.path.join(EXPORT_ROOT, note.slug)
    os.makedirs(out_dir, exist_ok=True)

    # 保存标题 & 正文
    title_path = os.path.join(out_dir, "note_title.txt")
    body_path = os.path.join(out_dir, "note_body.txt")

    with open(title_path, "w", encoding="utf-8") as f:
        f.write(note.title.strip() + "\n")

    with open(body_path, "w", encoding="utf-8") as f:
        f.write(note.body.strip() + "\n")

    # 拷贝图片
    for idx, src in enumerate(note.image_paths, start=1):
        if not os.path.exists(src):
            print(f"[WARN] 图片文件不存在，无法复制: {src}")
            continue
        ext = os.path.splitext(src)[1] or ".png"
        dst_name = f"img_{idx:02d}{ext}"
        dst = os.path.join(out_dir, dst_name)
        shutil.copy2(src, dst)
        print(f"[OK] 拷贝图片 -> {dst}")

    print(f"[OK] 导出素材包: {out_dir}")
    return out_dir


def export_all_notes() -> None:
    """
    一键导出：
    - 2021–2025 每年的所有文案段落；
    - 2021–2025 总趋势（trend）；
    并在 xhs_exports/INDEX.md 写一份索引。
    """
    os.makedirs(EXPORT_ROOT, exist_ok=True)

    all_notes: List[XHSNote] = []

    # 年度笔记
    for year in range(2021, 2026):
        try:
            year_notes = load_all_year_notes(year)
        except FileNotFoundError as e:
            print(f"[WARN] {e}")
            continue
        if not year_notes:
            print(f"[WARN] {year} 年没有可用文案。")
            continue
        all_notes.extend(year_notes)

    # 总趋势
    try:
        trend_note = load_trend_note()
        all_notes.append(trend_note)
    except FileNotFoundError as e:
        print(f"[WARN] {e}")

    if not all_notes:
        print("[WARN] 没有任何笔记被导出，请检查 llm_reports 目录。")
        return

    index_lines = [
        "# 小红书素材包索引\n",
        "以下是已经打包好的所有图文素材包：\n",
        "| slug | 标题 | 目录 |\n",
        "|------|------|------|\n",
    ]

    for note in all_notes:
        out_dir = export_note(note)
        rel_dir = os.path.relpath(out_dir, BASE_DIR)
        index_lines.append(
            f"| {note.slug} | {note.title.replace('|', '｜')} | `{rel_dir}` |\n"
        )

    index_path = os.path.join(EXPORT_ROOT, "INDEX.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.writelines(index_lines)

    print("\n========== 全量素材包导出完成 ==========")
    print(f"导出根目录: {EXPORT_ROOT}")
    print(f"索引文件: {index_path}")
    print("你可以打开 INDEX.md，挑选想发的 slug，然后到对应目录拖图 + 复制文字即可。")
    print("======================================\n")


# -------- CLI 主入口 --------

def main():
    parser = argparse.ArgumentParser(
        description="根据 topic(年份或trend) 自动打包小红书图文素材；或使用 --all 一次性打包全部。"
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--topic",
        help="2021 / 2022 / 2023 / 2024 / 2025 / trend 之一；若使用 --all 则可省略。",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="导出所有素材包（2021–2025 年度 + 趋势）。",
    )
    parser.add_argument(
        "--variant",
        type=int,
        default=1,
        help="对于年度文案，选第几条（1 或 2）。trend 或 --all 时忽略此参数。",
    )

    args = parser.parse_args()

    # 一键导出模式
    if args.all:
        export_all_notes()
        return

    # 单条导出模式：必须有 topic
    if not args.topic:
        parser.error("需要指定 --topic（年份或 trend），或使用 --all 一次性导出全部。")

    topic = args.topic.strip().lower()

    if topic == "trend":
        note = load_trend_note()
    else:
        try:
            year = int(topic)
        except ValueError:
            raise SystemExit("topic 只能是 2021–2025 或 'trend'")

        if year < 2021 or year > 2025:
            raise SystemExit("年度 topic 只支持 2021–2025 这几个整数。")

        note = load_year_note(year, variant=args.variant)

    out_dir = export_note(note)

    print("\n========== 单条素材包导出完成 ==========")
    print(f"导出目录: {out_dir}")
    print("发布步骤：")
    print("1. 打开小红书创作中心，选择『图文笔记』；")
    print("2. 将该目录下的 img_*.png 全部拖入上传区域；")
    print("3. 打开 note_title.txt 复制标题，note_body.txt 复制正文；")
    print("4. 补充话题/封面裁切后即可发布。")
    print("=====================================\n")


if __name__ == "__main__":
    main()
