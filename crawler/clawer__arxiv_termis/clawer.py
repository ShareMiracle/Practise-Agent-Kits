import argparse
import requests
import time
import csv
import os
import random
import re
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from fake_useragent import UserAgent  # 需安装：pip install fake_useragent

# -------------------------- 全局配置 --------------------------
DEFAULT_SEARCH_PHRASE = "medical image registration"  # 默认核心关键词：医学影像配准
SEARCH_PHRASE = DEFAULT_SEARCH_PHRASE  # 当前使用的关键词
MAX_RESULTS_PER_SITE = 5  
BASE_PDF_SAVE_DIR = "./multi_source_pdfs"  # PDF保存基础目录
PDF_SAVE_DIR = f"{BASE_PDF_SAVE_DIR}/{SEARCH_PHRASE.replace(' ', '_')}"  # PDF保存目录
BASE_CSV_PATH = "./multi_source_papers"  # 结果记录CSV基础路径
CSV_PATH = f"{BASE_CSV_PATH}_{SEARCH_PHRASE.replace(' ', '_')}.csv"  # 结果记录CSV
REQUEST_DELAY = (2, 4)  # 随机请求延迟（秒），降低反爬风险
DOWNLOAD_RETRIES = 3  # 下载失败重试次数
TIMEOUT = 60  # 超时时间（秒）

# 创建保存目录
os.makedirs(PDF_SAVE_DIR, exist_ok=True)
ua = UserAgent()  # 随机User-Agent生成器


# -------------------------- 工具函数 --------------------------
def get_random_headers():
    """生成随机请求头，模拟不同浏览器"""
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Referer": "https://www.ncbi.nlm.nih.gov/",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1"
    }


def get_pmc_specific_headers():
    """生成针对PMC PDF下载的特定请求头"""
    return {
        "User-Agent": ua.random,
        "Accept": "application/pdf,application/x-pdf,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://www.ncbi.nlm.nih.gov/pmc/articles/",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }


def is_valid_pdf(file_path):
    """验证PDF有效性（检查文件头和大小）"""
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 1024 * 10:  # 至少10KB
        return False
    with open(file_path, "rb") as f:
        return f.read(5) == b"%PDF-"  # PDF文件头标识


def safe_download(pdf_url, save_path):
    """带重试机制的PDF下载，解决连接重置/超时问题"""
    if is_valid_pdf(save_path):
        print(f"✅ 已存在有效PDF：{os.path.basename(save_path)}")
        return True
    for retry in range(DOWNLOAD_RETRIES):
        try:
            # 根据URL选择合适的请求头
            if "pmc" in pdf_url.lower():
                headers = get_pmc_specific_headers()
            else:
                headers = get_random_headers()
            print(f"📥 下载PDF（重试{retry+1}/{DOWNLOAD_RETRIES}）：{pdf_url}")
            response = requests.get(
                pdf_url,
                headers=headers,
                timeout=TIMEOUT,
                stream=True,  # 流式下载大文件
                allow_redirects=True
            )
            response.raise_for_status()  # 触发4xx/5xx错误
            # 分块写入（1MB/块），避免内存溢出
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            if is_valid_pdf(save_path):
                print(f"✅ 下载成功：{os.path.basename(save_path)}")
                return True
            else:
                os.remove(save_path)
                print(f"❌ 无效PDF文件，重试...")
        except Exception as e:
            print(f"❌ 下载失败（{str(e)}），重试...")
            if os.path.exists(save_path):
                os.remove(save_path)
            time.sleep(2 * (retry + 1))  # 重试间隔递增
    return False


# -------------------------- 1. arXiv爬取模块（预印本，无权限限制） --------------------------
def crawl_arxiv(max_results=None):
    print("\n===== 开始爬取arXiv =====")
    papers = []
    ns_uri = "http://www.w3.org/2005/Atom"  # XML命名空间
    # 精准搜索：标题/摘要包含关键词，且属于计算机视觉或医学物理领域
    search_query = f'"{SEARCH_PHRASE}" AND (cat:cs.CV OR cat:physics.med-ph)'
    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results if max_results is not None else MAX_RESULTS_PER_SITE,
        "sortBy": "submittedDate",  # 按提交日期排序（最新优先）
        "sortOrder": "descending"
    }
    try:
        # 调用arXiv API
        response = requests.get(
            "http://export.arxiv.org/api/query",
            params=params,
            headers=get_random_headers(),
            timeout=TIMEOUT
        )
        root = ET.fromstring(response.text)
        entries = root.findall(f".//{{{ns_uri}}}entry")  # 解析论文列表
        print(f"arXiv解析到{len(entries)}篇论文")

        for entry in entries:
            # 提取标题（改进：使用更通用的方式查找标题元素，处理不同的XML结构）
            title_elem = entry.find(f".//{{{ns_uri}}}title")
            title = ""
            if title_elem is not None:
                if title_elem.text:
                    title = title_elem.text.strip()
                elif title_elem.get_text():
                    title = title_elem.get_text().strip()
            title = title if title else "无标题"
            
            # 提取摘要并转为小写（用于过滤）
            summary_elem = entry.find(f".//{{{ns_uri}}}summary")
            summary = ""
            if summary_elem is not None:
                if summary_elem.text:
                    summary = summary_elem.text.lower()
                elif summary_elem.get_text():
                    summary = summary_elem.get_text().lower()
            summary = summary if summary else ""
            # 过滤无关论文（标题或摘要必须包含核心关键词）
            if SEARCH_PHRASE.lower() not in (title.lower() + summary):
                print(f"arXiv过滤无关：{title[:30]}...")
                continue
            # 提取PDF链接
            pdf_link = ""
            for link in entry.findall(f".//{{{ns_uri}}}link"):
                if link.get("type") == "application/pdf":
                    pdf_link = link.get("href")
                    break
            if not pdf_link:
                continue
            # 提取arXiv ID（用于文件名）
            arxiv_id_match = re.search(r"arxiv.org/(?:abs|pdf)/(\d+\.\d+)", pdf_link)
            if arxiv_id_match:
                arxiv_id = arxiv_id_match.group(1)
            else:
                # 备用匹配模式
                arxiv_id_match = re.search(r"arxiv.org/(?:abs|pdf)/([\w.-]+)", pdf_link)
                arxiv_id = arxiv_id_match.group(1).replace("/", "_") if arxiv_id_match else f"arxiv_{random.randint(1000000, 9999999)}"
            pdf_filename = f"arxiv_{arxiv_id}.pdf"
            pdf_path = os.path.join(PDF_SAVE_DIR, pdf_filename)
            # 下载PDF
            success = safe_download(pdf_link, pdf_path)
            # 提取作者
            authors = [auth.find(f".//{{{ns_uri}}}name").text for auth in entry.findall(f".//{{{ns_uri}}}author") 
                      if auth.find(f".//{{{ns_uri}}}name") is not None and auth.find(f".//{{{ns_uri}}}name").text is not None]
            # 保存论文信息
            papers.append({
                "source": "arXiv",
                "id": arxiv_id,
                "title": title,
                "authors": ", ".join(authors) if authors else "未知作者",
                "pdf_link": pdf_link,
                "pdf_path": pdf_path,
                "status": "成功" if success else "失败"
            })
            time.sleep(random.uniform(*REQUEST_DELAY))  # 随机延迟，模拟人类行为
    except Exception as e:
        print(f"arXiv爬取失败：{e}")
    return papers


# -------------------------- 辅助函数：设置当前主题 --------------------------
def set_search_phrase(phrase):
    """设置当前搜索关键词，并更新相关路径"""
    global SEARCH_PHRASE, PDF_SAVE_DIR, CSV_PATH
    SEARCH_PHRASE = phrase
    PDF_SAVE_DIR = f"{BASE_PDF_SAVE_DIR}/{SEARCH_PHRASE.replace(' ', '_')}"
    CSV_PATH = f"{BASE_CSV_PATH}_{SEARCH_PHRASE.replace(' ', '_')}.csv"
    # 创建保存目录
    os.makedirs(PDF_SAVE_DIR, exist_ok=True)
    print(f"\n===== 已设置搜索主题: {SEARCH_PHRASE} =====")

# -------------------------- 主函数：整合多平台结果 --------------------------
def multi_source_crawl(max_results=None):
    """为当前设置的主题执行爬取，只爬取arXiv论文
    
    Args:
        max_results: 爬取的论文数量，None表示使用默认值
    """
    all_papers = []
    # 只爬取arXiv
    all_papers.extend(crawl_arxiv(max_results=max_results))

    # 去重（按PDF链接，避免重复下载）
    unique_papers = []
    seen_links = set()
    for paper in all_papers:
        if paper["pdf_link"] not in seen_links:
            seen_links.add(paper["pdf_link"])
            unique_papers.append(paper)
    print(f"\n===== 去重后共{len(unique_papers)}篇论文 =====")

    # 保存结果到CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        if unique_papers:
            fieldnames = unique_papers[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_papers)
    print(f"结果已保存至：{CSV_PATH}")
    print(f"PDF文件保存目录：{os.path.abspath(PDF_SAVE_DIR)}")
    return unique_papers

# -------------------------- 批量爬取函数：支持多主题 --------------------------
def batch_crawl(topics):
    """批量爬取多个主题
    
    Args:
        topics: 主题列表，如 ["medical image registration", "computer vision"]
        
    Returns:
        dict: 每个主题对应的爬取结果
    """
    if not topics:
        print("警告：未提供主题列表，使用默认主题")
        topics = [DEFAULT_SEARCH_PHRASE]
    
    results = {}
    for topic in topics:
        print(f"\n{'='*50}")
        print(f"开始爬取主题: {topic}")
        print(f"{'='*50}")
        # 设置当前主题
        set_search_phrase(topic)
        # 执行爬取
        papers = multi_source_crawl()
        results[topic] = papers
    
    print(f"\n{'='*50}")
    print("批量爬取完成！")
    print(f"{'='*50}")
    for topic, papers in results.items():
        print(f"{topic}: {len(papers)}篇论文")
    
    return results


if __name__ == "__main__":
    # 自动安装依赖
    try:
        from fake_useragent import UserAgent
    except ImportError:
        print("安装fake_useragent...")
        os.system("pip install fake_useragent")
        from fake_useragent import UserAgent
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("安装beautifulsoup4...")
        os.system("pip install beautifulsoup4")
        from bs4 import BeautifulSoup
    
    # 创建保存目录
    os.makedirs(BASE_PDF_SAVE_DIR, exist_ok=True)
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='arXiv论文爬取工具')
    parser.add_argument('-n', '--num', type=int, default=None, help='爬取的论文数量')
    args = parser.parse_args()
    
    # 使用指定数量爬取arXiv论文
    multi_source_crawl(max_results=args.num)