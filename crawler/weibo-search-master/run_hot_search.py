# encoding: utf-8
import requests
from lxml import etree
from datetime import datetime
import os
import sys
from scrapy.cmdline import execute
from scrapy.utils.project import get_project_settings
 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

HOT_URL = "https://tophub.today/n/KqndgxeLl9"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.69',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': 'https://tophub.today/'
}
MAX_HOT_KEYWORDS = 50
MAX_ITEMS_PER_KEYWORD = 1000
TODAY = datetime.now().strftime("%Y-%m-%d")


def safe_extract_text(xpath_result):
    try:
        return xpath_result[0].strip() if xpath_result and xpath_result[0].strip() else ""
    except (IndexError, AttributeError):
        return ""


def crawl_hot_keywords():
    hot_keywords = []
    print("=" * 80)
    print("📌 开始爬取微博热搜关键词（转换为话题格式）")
    print("=" * 80)

    try:
        response = requests.get(url=HOT_URL, headers=HEADERS, timeout=15)
        response.encoding = "utf-8"
        html = etree.HTML(response.text)

        trs = html.xpath(
            '//div[contains(@class, "jc rank-all-item")]//div[@class="jc-c"]//table[@class="table"]//tbody/tr'
        )

        if not trs:
            print("❌ 未找到热搜数据，请检查XPath或数据源URL！")
            return hot_keywords

        print(f"✅ 找到 {len(trs)} 条热搜（爬取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）")
        print("-" * 150)

        for i, tr in enumerate(trs):
            if i >= MAX_HOT_KEYWORDS:  # 限制只取前N个热搜
                break

            # 提取热搜信息
            rank = safe_extract_text(tr.xpath('./td[1]/text()')).replace('.', '')
            title = safe_extract_text(tr.xpath('./td[2]/a/text()'))
            hot_value = safe_extract_text(tr.xpath('./td[3]/text()'))

            # 过滤广告和无效标题
            if not title or "广告" in title:
                print(f"❌ 跳过无效热搜（排名{rank}：{title}）")
                continue

            # 转换为话题格式：首尾添加#号
            keyword = '#' + title.replace("#", "").strip() + '#'
            hot_keywords.append(keyword)

            print(f"排名：{rank:2s} | 标题：{title:<30} | 热度：{hot_value:8s} | 话题关键词：{keyword}")

        print("-" * 150)
        print(f"✅ 成功提取 {len(hot_keywords)} 个有效话题关键词")
        print("=" * 80)

    except requests.exceptions.RequestException as e:
        print(f"❌ 热搜爬取失败（网络错误）：{str(e)}")
    except Exception as e:
        print(f"❌ 热搜爬取失败（其他错误）：{str(e)}")

    return hot_keywords


def start_weibo_crawler(keywords):
    if not keywords:
        print("❌ 无有效关键词，爬虫启动失败！")
        return

    print("\n" + "=" * 80)
    print(f"🚀 启动微博搜索爬虫（单次测试模式）")
    print(f"🔍 搜索关键词：{len(keywords)} 个")
    print(f"📅 搜索时间：{TODAY}（当天）")
    print(f"📊 限制条数：每个关键词前{MAX_ITEMS_PER_KEYWORD}条")
    print("=" * 80)

    try:
        # 关键修改：通过-a参数传递关键词给爬虫
        cmd = [
            'scrapy', 'crawl', 'search',
            '-a', f'keywords={",".join(keywords)}',  # 直接传递关键词列表
            '-s', f'START_DATE={TODAY}',
            '-s', f'END_DATE={TODAY}',
            '-s', f'MAX_ITEMS_PER_KEYWORD={MAX_ITEMS_PER_KEYWORD}',
            '-s', 'DOWNLOAD_DELAY=3',
            '-s', 'CONCURRENT_REQUESTS=1',
            '-s', 'LOG_LEVEL=INFO'
        ]
        execute(cmd)

    except Exception as e:
        print(f"❌ 爬虫运行失败：{str(e)}")


if __name__ == "__main__":
    hot_keywords = crawl_hot_keywords()
    start_weibo_crawler(hot_keywords)
