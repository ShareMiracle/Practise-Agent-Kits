"""
轻量级论文助手：
1) 使用 Google Scholar 按关键词搜索并列出论文（优先 SerpAPI，支持 scholarly 回退）；
2) 允许选择论文，直接从论文网页提取正文与图片（不再强制下载 PDF）；
3) 调用 SiliconFlow API（Qwen/QwQ-32B）生成中文解读与总结。
（暂不包含发布到小红书的步骤）。

依赖：
- requests（必需，用于HTTP请求与API调用）
- pypdf 或 PyPDF2（提取文本）
- pymupdf/fitz（可选，提取图片）
- scholarly（可选，无 SerpAPI 时可用）

环境变量：
- SERPAPI_API_KEY：使用 SerpAPI 的 Google Scholar 搜索密钥（推荐）
- SILICONFLOW_API_KEY：SiliconFlow API 密钥（调用大模型时必填）
- 若未提供 SERPAPI_API_KEY，将 fallback 到内置 key（b8b1c35a357875a42cad73c2bb40893b145af7bebe5dad82fc202905175cf2ec）
"""

from __future__ import annotations

import argparse
from pathlib import Path
import os

from models import Paper
from pdf_utils import fetch_html_content, PaperDownloader, PDFContentExtractor
from llm_client import LLMInterpreter
from reporting import ReportComposer
from search_module import ScholarSearcher, ArxivSearcher
# 小红书发布相关已移除


def run_pipeline(args: argparse.Namespace) -> None:
    serpapi_key = getattr(args, "serpapi_key", None)
    # 选择搜索器：支持 Google Scholar（SerpAPI / scholarly）或 arXiv
    if args.search_backend == "arxiv":
        searcher = ArxivSearcher()
    else:
        searcher = ScholarSearcher(serpapi_key, backend=args.search_backend)
    papers = searcher.search(args.keywords, args.limit)
    if not papers:
        raise RuntimeError("未找到匹配的论文。")
    print("\n搜索结果：")
    for idx, paper in enumerate(papers, 1):
        print(f"[{idx}] {paper.title} {paper.year or ''}")
        if paper.authors:
            print(f"    作者：{', '.join(paper.authors)}")
        if paper.snippet:
            print(f"    摘要：{paper.snippet}")
        print(f"    链接：{paper.link}")
        if paper.pdf_url:
            print(f"    PDF：{paper.pdf_url}")
    selection = args.pick
    if selection is None:
        selection = int(input("\n请选择要解读的编号：").strip() or 1)
    paper = papers[selection - 1]

    fig_dir = Path(args.fig_dir)
    # 优先：若存在 PDF 链接则下载到指定目录并从 PDF 中提取内容；失败则降级为网页抓取
    download_dir = Path(args.download_dir)
    pdf_path = None
    if paper.pdf_url:
        downloader = PaperDownloader(download_dir)
        try:
            pdf_path = downloader.download_pdf(paper)
            print(f"已下载 PDF 到：{pdf_path}")
        except Exception as exc:  # 下载失败则记录并降级
            print(f"PDF 下载失败，改为从网页抓取：{exc}")

    if pdf_path is not None:
        extractor = PDFContentExtractor(max_pages=args.max_pages)
        text = extractor.extract_text(pdf_path)
        # 传入 None 表示不限制图片数量，提取 PDF 中所有图片
        figures = extractor.extract_figures(pdf_path, fig_dir, limit=None, filename_prefix=paper.title)
    else:
        target_url = paper.link or paper.pdf_url
        if not target_url:
            raise RuntimeError("该条目既没有网页链接也没有 PDF 链接，无法获取内容。")
        print(f"直接从网页读取内容：{target_url}")
        text, figures = fetch_html_content(target_url, fig_dir, max_images=args.max_figures, filename_prefix=paper.title)

    interpreter = LLMInterpreter(
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        provider=args.provider,
    )
    summary = interpreter.summarize(paper, text, args.extra)

    composer = ReportComposer(Path(args.output_dir))
    report_path = composer.write_markdown(paper, summary, figures)
    print(f"总结已生成：{report_path}")
    if figures:
        print("提取的图片：")
        for fig in figures:
            print(f"- {fig}")

    # 小红书发布功能已移除（如需恢复，请在 publish_xhs.py 中实现并导入）


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="论文搜索与解读助手（不含发布功能）")
    parser.add_argument("--keywords", required=True, help="检索关键词（用于 Google Scholar 或 arXiv 等）")
    parser.add_argument("--limit", type=int, default=5, help="返回文献数量")
    parser.add_argument("--pick", type=int, help="直接选择解读的序号，省略则交互选择")
    parser.add_argument(
        "--serpapi-key",
        dest="serpapi_key",
        default=None,
        help="SerpAPI 密钥（也可用环境变量 SERPAPI_API_KEY，缺省使用内置默认值）",
    )
    parser.add_argument(
        "--search-backend",
        choices=["auto", "serpapi", "scholarly", "arxiv"],
        default="auto",
        help=(
            "搜索后端：'arxiv' 使用 arXiv API；'auto'（默认）优先 SerpAPI（若提供 key），"
            "失败再尝试 scholarly；或手动指定 serpapi/scholarly。"
        ),
    )
    parser.add_argument("--download-dir", default="/home/bowenliu/agent/article", help="PDF 下载目录")
    parser.add_argument("--fig-dir", default="/home/bowenliu/agent/data/figures", help="图片输出目录")
    parser.add_argument("--output-dir", default="/home/bowenliu/agent/data/reports", help="Markdown 输出目录")
    parser.add_argument("--max-pages", type=int, default=11, help="用于总结的最大页数")
    parser.add_argument("--max-figures", type=int, default=3, help="最多提取的图片数量")
    parser.add_argument(
        "--api-key",
        help="SiliconFlow API 密钥（默认读取 SILICONFLOW_API_KEY 环境变量）",
    )
    parser.add_argument(
        "--base-url",
        help="SiliconFlow API Base URL（默认为 https://api.siliconflow.cn/v1/chat/completions）",
    )
    parser.add_argument(
        "--model",
        default="Qwen/QwQ-32B",
        help="大模型名称（默认 Qwen/QwQ-32B）",
    )
    parser.add_argument("--temperature", type=float, default=0.2, help="生成温度")
    parser.add_argument("--max-tokens", type=int, default=1024, help="总结的最大输出 token 数")
    parser.add_argument("--extra", help="额外的总结要求")
    parser.add_argument(
        "--provider",
        choices=["siliconflow"],
        default="siliconflow",
        help="大模型提供方，默认使用 SiliconFlow",
    )
    # 小红书发布选项（已移除）
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()


# 示例：
# python agent.py --keywords "attention" --search-backend arxiv --limit 5 