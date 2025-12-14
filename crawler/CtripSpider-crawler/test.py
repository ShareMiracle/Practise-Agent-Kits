import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time
import random
import json

# 携程景点评论页面的URL模板
# 使用上海迪士尼的评论页作为示例
BASE_URL_TEMPLATE = "https://you.ctrip.com/sight/shanghai2/1412255-review-p{page}.html"

# 伪装请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

def parse_comments_from_html(html_content):
    """
    使用BeautifulSoup解析HTML内容，提取评论数据
    使用之前分析的通用携程评论结构进行解析
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    comments_list = []

    # 尝试定位评论列表项
    # 携程评论列表项的class通常是 'comment_item' 或 'review_item'
    comment_items = soup.find_all('div', class_=lambda x: x and ('comment_item' in x or 'review_item' in x))
    
    if not comment_items:
        # 检查是否有明显的反爬提示
        if soup.find('div', class_='captcha_container') or "登录" in soup.text[:1000]:
             print("警告：页面可能触发反爬机制，返回了验证码或登录提示。")
        else:
             print("警告：未找到评论元素。请检查HTML结构是否已更改。")
        return []

    for item in comment_items:
        try:
            # 提取评论内容
            content_tag = item.find('div', class_=lambda x: x and ('comment_content' in x or 'text' in x))
            content = content_tag.get_text(strip=True) if content_tag else "内容缺失"
            
            # 提取用户名 
            user_tag = item.find('span', class_=lambda x: x and ('user_name' in x or 'name' in x))
            user = user_tag.get_text(strip=True) if user_tag else "匿名用户"
            
            # 提取评分 (通常通过class或属性表示)
            score_tag = item.find('div', class_=lambda x: x and ('score_star' in x or 'star_rating' in x))
            score = score_tag.get('data-score') if score_tag and score_tag.get('data-score') else "评分缺失"
            
            comments_list.append({
                "user": user,
                "content": content,
                "score": score
            })
        except Exception as e:
            # print(f"解析单条评论时出错: {e}")
            continue

    return comments_list

async def scrape_ctrip_reviews_dynamic(resource_id, total_pages=10, page_size=10):
    """
    使用Playwright模拟浏览器行为，爬取动态加载的评论数据
    """
    all_comments = []
    print(f"开始使用 Playwright 爬取景点ID {resource_id} 的评论数据，预计爬取 {total_pages} 页...")

    async with async_playwright() as p:
        # 使用 Chromium 浏览器，headless=True 表示无头模式
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=HEADERS["User-Agent"])
        page = await context.new_page()

        for page_index in range(1, total_pages + 1):
            # 构造分页URL
            page_url = BASE_URL_TEMPLATE.format(page=page_index)
            print(f"--- 正在尝试爬取第 {page_index} 页: {page_url} ---")

            try:
                # 导航到页面
                response = await page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
                
                # 检查是否被重定向或返回错误状态码
                if response.status >= 400:
                    print(f"警告：页面返回状态码 {response.status}，可能触发反爬。")
                    break

                # 等待评论列表加载完成
                # 假设评论列表容器的class是 'comment_list' 或 'review_list'
                await page.wait_for_selector('div[class*="comment_item"], div[class*="review_item"]', timeout=10000)
                
                # 获取完整的HTML内容
                html_content = await page.content()
                
                # 解析HTML
                comments = parse_comments_from_html(html_content)
                
                if not comments:
                    print(f"第 {page_index} 页未找到评论，可能已到最后一页或触发反爬。停止爬取。")
                    break
                
                all_comments.extend(comments)
                print(f"成功爬取 {len(comments)} 条评论，累计 {len(all_comments)} 条。")
                
                # 随机延迟
                await asyncio.sleep(random.uniform(2, 5))

            except Exception as e:
                print(f"爬取第 {page_index} 页时发生错误: {e}")
                break

        await browser.close()
    return all_comments

if __name__ == '__main__':
    # ----------------------------------------------------------------
    # **重要：请将 RESOURCE_ID 替换为您要爬取的景点ID**
    # ----------------------------------------------------------------
    RESOURCE_ID = 1412255 
    
    # 爬取前3页数据进行测试
    results = asyncio.run(scrape_ctrip_reviews_dynamic(RESOURCE_ID, total_pages=3))
    
    if results:
        print("\n--- 爬取结果摘要 ---")
        print(f"总共爬取到 {len(results)} 条评论。")
        
        # 打印前5条评论示例
        for i, comment in enumerate(results[:5]):
            print(f"[{i+1}] 用户: {comment['user']}, 评分: {comment['score']}, 内容: {comment['content'][:50]}...")
            print("-" * 20)
            
        # 示例：写入JSON文件
        with open(f"ctrip_reviews_dynamic_{RESOURCE_ID}.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n数据已保存到 ctrip_reviews_dynamic_{RESOURCE_ID}.json")
    else:
        print("未爬取到任何评论数据。")