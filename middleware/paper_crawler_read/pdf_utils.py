from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Optional

import requests

from models import Paper

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN,zh;q=0.8",
}


class PaperDownloader:
    def __init__(self, download_dir: Path):
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download_pdf(self, paper: Paper) -> Path:
        url = paper.pdf_url or paper.link
        if not url:
            raise RuntimeError("未找到可下载的链接。")
        filename = self._safe_filename(f"{paper.title}.pdf")
        target = self.download_dir / filename
        resp = requests.get(url, stream=True, timeout=30, headers=DEFAULT_HEADERS)
        resp.raise_for_status()
        with target.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return target

    @staticmethod
    def _safe_filename(name: str) -> str:
        cleaned = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", "."))
        cleaned = cleaned.strip().replace(" ", "_")
        return cleaned or "paper.pdf"


class PDFContentExtractor:
    def __init__(self, max_pages: int = 8):
        self.max_pages = max_pages
        self._reader_cls = self._load_pdf_reader()

    @staticmethod
    def _load_pdf_reader():
        try:
            from pypdf import PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfReader  # type: ignore
            except ImportError as exc:  # noqa: PERF203
                raise RuntimeError("未找到 pypdf 或 PyPDF2，用于提取文本。") from exc
        return PdfReader

    def extract_text(self, pdf_path: Path) -> str:
        reader = self._reader_cls(str(pdf_path))
        pages = reader.pages[: self.max_pages] if hasattr(reader, "pages") else []
        texts = []
        for page in pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(texts).strip()

    def extract_figures(self, pdf_path: Path, output_dir: Path, limit: Optional[int] = 3, filename_prefix: Optional[str] = None) -> List[Path]:
        try:
            import fitz  # pymupdf
        except ImportError:
            return []
        output_dir.mkdir(parents=True, exist_ok=True)
        fig_paths: List[Path] = []
        doc = fitz.open(str(pdf_path))
        # 生成安全的文件名前缀
        if filename_prefix:
            cleaned = "".join(c for c in filename_prefix if c.isalnum() or c in (" ", "-", "_", "."))
            cleaned = cleaned.strip().replace(" ", "_")
            prefix = cleaned or "paper"
        else:
            prefix = "paper"
        for page_index, page in enumerate(doc):
            if limit is not None and len(fig_paths) >= limit:
                break
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                if limit is not None and len(fig_paths) >= limit:
                    break
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha < 4:  # RGB 或灰度
                    image = pix
                else:
                    image = fitz.Pixmap(fitz.csRGB, pix)
                # 构建文件名：{prefix}_img{n}.{ext}
                n = len(fig_paths) + 1
                out_path = output_dir / f"{prefix}_img{n}.png"
                image.save(out_path)
                fig_paths.append(out_path)
                image = None  # 释放资源
        return fig_paths


def fetch_html_content(url: str, fig_dir: Path, max_images: int = 3, filename_prefix: Optional[str] = None) -> Tuple[str, List[Path]]:
    """
    从论文网页提取文本与若干图片，作为 PDF 下载失败时的降级方案。
    """
    resp = requests.get(url, timeout=30, headers=DEFAULT_HEADERS)
    if resp.status_code == 403:
        raise RuntimeError(f"网页访问被拒绝(403)：{url}，该站点可能需要登录或订阅权限，当前脚本无法自动抓取。")
    resp.raise_for_status()
    html = resp.text

    text = ""
    fig_paths: List[Path] = []

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        chunks = []
        for node in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            t = node.get_text(strip=True)
            if t:
                chunks.append(t)
        text = "\n".join(chunks)

        from urllib.parse import urljoin

        img_urls = []
        # 从 <img> 的多种属性抓取图片（支持 lazy loading）
        src_attrs = ["src", "data-src", "data-original", "data-lazy-src", "data-actualsrc", "data-srcset", "srcset"]
        for img in soup.find_all("img"):
            found = None
            for attr in src_attrs:
                val = img.get(attr)
                if not val:
                    continue
                # 跳过 base64 内嵌图片
                if val.startswith("data:"):
                    continue
                # 若是 srcset，取第一个 URL
                if attr in ("srcset", "data-srcset"):
                    parts = [p.strip() for p in val.split(",") if p.strip()]
                    if parts:
                        # 每部分可能形如 "url 1x"，取第一个 token
                        first = parts[0].split()[0]
                        found = first
                        break
                else:
                    found = val
                    break
            if found:
                img_urls.append(urljoin(url, found))

        # 也从 <a href> 中抓取直接指向图片文件的链接
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            if not href:
                continue
            if href.startswith("data:"):
                continue
            low = href.lower()
            if any(low.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
                img_urls.append(urljoin(url, href))

        # 从 style 属性中解析 background-image: url(...)
        import re

        style_url_re = re.compile(r"background(?:-image)?\s*:\s*url\(([^)]+)\)", re.I)
        for elem in soup.find_all(True):
            style = elem.get("style")
            if not style:
                continue
            m = style_url_re.search(style)
            if m:
                raw = m.group(1).strip(' "\'')
                if raw and not raw.startswith("data:"):
                    img_urls.append(urljoin(url, raw))

        # 去重但保持顺序
        seen = set()
        deduped_img_urls = []
        for u in img_urls:
            if u in seen:
                continue
            seen.add(u)
            deduped_img_urls.append(u)
        img_urls = deduped_img_urls

        fig_dir.mkdir(parents=True, exist_ok=True)
        # 生成安全前缀
        if filename_prefix:
            cleaned = "".join(c for c in filename_prefix if c.isalnum() or c in (" ", "-", "_", "."))
            cleaned = cleaned.strip().replace(" ", "_")
            prefix = cleaned or "paper"
        else:
            prefix = "paper"

        for idx, img_url in enumerate(img_urls[:max_images], start=1):
            try:
                img_resp = requests.get(img_url, stream=True, timeout=20, headers=DEFAULT_HEADERS)
                img_resp.raise_for_status()
            except Exception:
                continue
            # 尝试从 URL 后缀或 Content-Type 推断文件后缀
            suffix = ".png"
            # 优先用 URL 后缀
            from urllib.parse import urlparse

            path = urlparse(img_url).path
            if "." in path:
                ext = path.split(".")[-1].lower()
                if ext in ("png", "jpg", "jpeg", "gif", "svg", "webp"):
                    suffix = f".{ext}"
            # 若 URL 无后缀，再依据 Content-Type
            ctype = (img_resp.headers.get("Content-Type") or "").lower()
            if any(k in ctype for k in ("jpeg", "jpg")):
                suffix = ".jpg"
            elif "png" in ctype:
                suffix = ".png"
            elif "gif" in ctype:
                suffix = ".gif"
            elif "svg" in ctype:
                suffix = ".svg"
            elif "webp" in ctype:
                suffix = ".webp"

            img_path = fig_dir / f"{prefix}_img{idx}{suffix}"
            try:
                with img_path.open("wb") as f:
                    for chunk in img_resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                fig_paths.append(img_path)
            except Exception:
                # 写文件失败则跳过
                continue
    else:
        import re

        text = re.sub(r"<[^>]+>", "", html)

    return text.strip(), fig_paths
