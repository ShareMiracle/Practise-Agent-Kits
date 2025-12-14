# hakimi_crawler.py
# 简单的“哈基米梗”文本爬虫
# 功能：从指定网址出发，抓取页面文本中包含“哈基米”等关键词的句子，保存到 jsonl 文件

import requests
import time
import random
import json
import re
from urllib.parse import urljoin, urlparse
from collections import deque

from bs4 import BeautifulSoup

# ===================== 配置区域 =====================

# 你想爬的起始页面（根据自己情况替换）
# 注意：请只填写你**确认允许爬取**、且不需要登录的公开页面
SEED_URLS = [
    # 下面是示例，实际使用前请确认对应网站的服务条款 / robots.txt
    # "https://regengbaike.com/1833.html",
    # "https://www.sohu.com/a/752211921_121723580",
    # "https://www.toutiao.com/zixun/7514947376646277131/",
    # "https://www.zhihu.com/question/11191142061",
    "https://www.bilibili.com/opus/1062047139181363216",
]

# 限制只在这些域名里爬，防止爬跑偏
ALLOWED_DOMAINS = [
    "regengbaike.com",
    "sohu.com",
    "toutiao.com",
    "zhihu.com",
    "bilibili.com",
]

# 关键词：包含这些就认为是“哈基米相关”
KEYWORDS = [
    "哈基米",
    "哈吉米",
    "hachimi",
    "哈基米~",
    "哈基米！",
    # 如果有别的变体，可以自己继续加
]

# 保存结果的文件
OUTPUT_FILE = "output/corpus/hakimi_corpus.jsonl"

# 最大爬取页面数量 / 深度限制，防止跑飞
MAX_PAGES = 50

# 请求头（伪装一下正常浏览器）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HakimiBot/0.1; +https://example.com/bot-info)"
}

# 每个请求之间随机 sleep，避免太频繁
SLEEP_RANGE = (1, 3)  # 秒


# ===================== 工具函数 =====================

def is_allowed(url):
    """判断 URL 是否在允许的域名里"""
    try:
        netloc = urlparse(url).netloc
        # 去掉子域名前的 www.
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return any(netloc.endswith(domain) for domain in ALLOWED_DOMAINS)
    except Exception:
        return False


def fetch_html(url):
    """请求网页，返回 HTML 文本；失败返回 None"""
    try:
        print(f"[fetch] {url}")
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"[warn] status {resp.status_code} for {url}")
            return None
        # 自动猜测编码
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as e:
        print(f"[error] fetch {url} failed: {e}")
        return None


def extract_links(html, base_url):
    """从页面中提取链接，转成绝对地址，并按域名过滤"""
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        # 拼成绝对 URL
        full = urljoin(base_url, href)
        # 简单过滤 http/https
        if full.startswith("http://") or full.startswith("https://"):
            if is_allowed(full):
                links.add(full)
    return links


def extract_hakimi_snippets(html, url):
    """
    从页面文本中提取包含哈基米相关内容的“句子片段”
    返回：列表，每个元素是 dict: {"url": ..., "text": ..., "keywords": [...]}
    """
    soup = BeautifulSoup(html, "html.parser")
    snippets = []

    # 把页面中常见的文本标签扫一遍
    for tag in soup.find_all(["p", "span", "div", "li"]):
        text = tag.get_text(separator="", strip=True)
        if not text:
            continue
        # 去掉特别短的文本（比如几个字的菜单）
        if len(text) < 5:
            continue

        # 判断是否包含关键词
        if any(k in text for k in KEYWORDS):
            # 为了更干净，把较长文本按句子拆分
            # 这里用中文句号/问号/叹号 + 中英文 ?! 拆分
            sentences = re.split(r"[。！？!?]", text)
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if any(k in sent for k in KEYWORDS):
                    snippets.append(
                        {
                            "url": url,
                            "text": sent,
                            "keywords": [k for k in KEYWORDS if k in sent],
                        }
                    )
    return snippets


def save_snippets(snippets, output_file):
    """把结果追加写入 jsonl 文件（一行一个 json）"""
    if not snippets:
        return
    with open(output_file, "a", encoding="utf-8") as f:
        for item in snippets:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def crawl(seed_urls, max_pages=50):
    """简单的 BFS 爬虫主逻辑"""
    visited = set()
    queue = deque(seed_urls)
    pages_count = 0

    while queue and pages_count < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        if not is_allowed(url):
            print(f"[skip] not allowed domain: {url}")
            continue

        html = fetch_html(url)
        if html is None:
            continue

        # 1. 提取哈基米相关句子
        snippets = extract_hakimi_snippets(html, url)
        if snippets:
            print(f"[hit] {url} -> {len(snippets)} snippets")
            save_snippets(snippets, OUTPUT_FILE)
        else:
            print(f"[no-hit] {url}")

        # 2. 提取新链接加入队列（仅在同域名内扩散）
        new_links = extract_links(html, url)
        for link in new_links:
            if link not in visited:
                queue.append(link)

        pages_count += 1

        # 控制频率，避免太猛
        sleep_time = random.uniform(*SLEEP_RANGE)
        print(f"[info] crawled {pages_count} pages, sleep {sleep_time:.2f}s\n")
        time.sleep(sleep_time)


# ===================== 程序入口 =====================

if __name__ == "__main__":
    if not SEED_URLS:
        print("请先在 SEED_URLS 中配置起始网址，再运行本脚本。")
    else:
        print("=== Hakimi Crawler Start ===")
        print(f"Seed URLs: {len(SEED_URLS)}, Max pages: {MAX_PAGES}")
        crawl(SEED_URLS, max_pages=MAX_PAGES)
        print("=== Hakimi Crawler Done ===")
