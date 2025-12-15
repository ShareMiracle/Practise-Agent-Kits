from __future__ import annotations

import os
from typing import List, Optional

import requests

try:
    from scholarly import scholarly
except ImportError:  # scholarly 为可选依赖
    scholarly = None

from models import Paper

DEFAULT_SERPAPI_KEY = "b8b1c35a357875a42cad73c2bb40893b145af7bebe5dad82fc202905175cf2ec"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class ScholarSearcher:
    """Google Scholar 搜索，支持 SerpAPI、scholarly（HTML 抓取）等后端。"""

    def __init__(self, serpapi_key: Optional[str] = None, backend: str = "auto"):
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_API_KEY") or DEFAULT_SERPAPI_KEY
        self.backend = backend.lower()

    def search(self, query: str, limit: int = 5) -> List[Paper]:
        backend = self.backend
        if backend == "serpapi":
            return self._search_serpapi(query, limit)
        if backend == "scholarly":
            return self._search_scholarly(query, limit)

        # auto：如提供 SerpAPI key 则优先 SerpAPI，否则尝试 scholarly，再回退 SerpAPI
        errors = []
        if self.serpapi_key:
            try:
                return self._search_serpapi(query, limit)
            except Exception as exc:  # noqa: PERF203
                errors.append(exc)
        if scholarly:
            try:
                return self._search_scholarly(query, limit)
            except Exception as exc:  # type: ignore[unused-ignore]  # noqa: PERF203
                errors.append(exc)
        if errors:
            raise RuntimeError(f"所有搜索方式均失败：{errors}")
        raise RuntimeError("未找到搜索方式：请提供 SERPAPI_API_KEY 或安装 scholarly 库。")

    def _search_serpapi(self, query: str, limit: int) -> List[Paper]:
        if not self.serpapi_key:
            raise RuntimeError("未配置 SerpAPI 密钥。")
        params = {
            "engine": "google_scholar",
            "q": query,
            "api_key": self.serpapi_key,
            "num": min(limit, 20),
            "hl": "zh-CN",
        }
        resp = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        papers: List[Paper] = []
        for item in data.get("organic_results", [])[:limit]:
            info = item.get("publication_info", {}) or {}
            resources = item.get("resources", []) or []
            pdf_url = next((r.get("link") for r in resources if r.get("file_format") == "PDF"), None)
            authors = [a.get("name") for a in info.get("authors", []) if isinstance(a, dict)]
            year = None
            if isinstance(info.get("year"), int):
                year = info["year"]
            papers.append(
                Paper(
                    title=item.get("title", "未命名"),
                    link=item.get("link") or item.get("all_versions", [{}])[0].get("link", ""),
                    pdf_url=pdf_url,
                    snippet=item.get("snippet"),
                    authors=authors,
                    year=year,
                )
            )
        return papers


class ArxivSearcher:
    """基于 arXiv API 的简易搜索器，返回 Paper 列表。"""

    API_URL = "http://export.arxiv.org/api/query"

    def __init__(self):
        pass

    def search(self, query: str, limit: int = 5) -> List[Paper]:
        # 构造查询，使用 all: 搜索域匹配所有字段
        q = query.replace(" ", "+")
        params = {
            "search_query": f"all:{q}",
            "start": 0,
            "max_results": min(limit, 100),
        }
        resp = requests.get(self.API_URL, params=params, timeout=20, headers=DEFAULT_HEADERS)
        resp.raise_for_status()
        # 解析 Atom feed（使用内建 xml 库以减少依赖）
        import xml.etree.ElementTree as ET

        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers: List[Paper] = []
        for entry in root.findall("atom:entry", ns)[:limit]:
            title_el = entry.find("atom:title", ns)
            id_el = entry.find("atom:id", ns)
            summary_el = entry.find("atom:summary", ns)
            published_el = entry.find("atom:published", ns)
            title = title_el.text.strip() if title_el is not None and title_el.text else "未命名"
            id_url = id_el.text.strip() if id_el is not None and id_el.text else ""
            # arXiv 的 PDF 链接可由 abs->pdf 构造
            pdf_url = None
            if "/abs/" in id_url:
                pdf_url = id_url.replace("/abs/", "/pdf/") + ".pdf"
            summary = summary_el.text.strip() if summary_el is not None and summary_el.text else None
            authors = []
            for a in entry.findall("atom:author", ns):
                name_el = a.find("atom:name", ns)
                if name_el is not None and name_el.text:
                    authors.append(name_el.text.strip())
            year = None
            if published_el is not None and published_el.text:
                try:
                    year = int(published_el.text.strip()[:4])
                except Exception:
                    year = None
            papers.append(
                Paper(
                    title=title,
                    link=id_url,
                    pdf_url=pdf_url,
                    snippet=summary,
                    authors=authors,
                    year=year,
                )
            )
        return papers

    def _search_scholarly(self, query: str, limit: int) -> List[Paper]:
        if not scholarly:
            raise RuntimeError("scholarly 库不可用，无法直接抓取谷歌学术。")
        results = scholarly.search_pubs(query)
        papers: List[Paper] = []
        for _ in range(limit):
            try:
                item = next(results)
            except StopIteration:
                break
            bib = item.get("bib", {})
            links = item.get("eprint_url")
            papers.append(
                Paper(
                    title=bib.get("title", "未命名"),
                    link=item.get("pub_url", ""),
                    pdf_url=links if isinstance(links, str) and links.endswith(".pdf") else None,
                    snippet=None,
                    authors=bib.get("author", "").split(" and ") if bib.get("author") else [],
                    year=bib.get("pub_year"),
                )
            )
        return papers

