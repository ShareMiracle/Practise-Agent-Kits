from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Sequence

from models import Paper
from pdf_utils import PaperDownloader


class ReportComposer:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_markdown(self, paper: Paper, summary: str, figures: Sequence[Path]) -> Path:
        filename = PaperDownloader._safe_filename(f"{paper.title}.md")
        out_path = self.output_dir / filename
        fig_md = "\n".join(f"![图 {idx+1}]({path})" for idx, path in enumerate(figures))
        # 基本内容（始终包含）
        content_parts = [
            f"# {paper.title}",
            "",
            f"- 作者：{', '.join(paper.authors) if paper.authors else '未知'}",
            f"- 年份：{paper.year or '未知'}",
            f"- 链接：{paper.link}",
            "",
            "## 解读",
            summary,
        ]

        # 仅当有图片时才添加图片段落（避免输出提示性占位文本）
        if figures:
            content_parts.extend(["", "## 图片", fig_md])

        content = textwrap.dedent("\n".join(content_parts)).strip()
        out_path.write_text(content, encoding="utf-8")
        return out_path

