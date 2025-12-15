import asyncio
import sys
import argparse
import os

# 导入配置和爬虫模块 (确保在爬虫环境下能跑通)
import config
from media_platform.xhs import XiaoHongShuCrawler
from var import crawler_type_var
from tools import utils

async def main(keyword):
    # ==============================
    # 1. 动态配置参数
    # ==============================
    config.PLATFORM = "xhs"
    config.CRAWLER_TYPE = "search"
    config.KEYWORDS = keyword
    
    # 核心限制
    config.CRAWLER_MAX_NOTES_COUNT = 20
    config.SAVE_DATA_OPTION = "json"
    
    # 评论配置
    config.ENABLE_GET_COMMENTS = True
    config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 20
    config.ENABLE_GET_SUB_COMMENTS = True
    config.ENABLE_GET_MEIDAS = True  # 开启开关以触发逻辑，具体下载由 core.py 控制
    
    # 无头模式 (MCP调用时建议为False，除非你确信能全自动过验证)
    config.HEADLESS = False 
    
    crawler_type_var.set(config.CRAWLER_TYPE)

    # ==============================
    # 2. 启动爬虫
    # ==============================
    crawler = XiaoHongShuCrawler()
    await crawler.start()
    
    # ==============================
    # 3. 输出结果路径 (这是给 MCP 看的关键信息)
    # ==============================
    date_str = utils.get_current_date()
    cwd = os.getcwd()
    json_dir = os.path.join(cwd, "data", "xhs", "json")
    
    # 构造文件名
    content_file = os.path.join(json_dir, f"search_contents_{date_str}.json")
    comment_file = os.path.join(json_dir, f"search_comments_{date_str}.json")
    
    # 用特殊标记打印结果，方便 MCP 提取
    print(f"__RESULT_PATH_START__")
    print(f"Contents: {content_file}")
    print(f"Comments: {comment_file}")
    print(f"__RESULT_PATH_END__")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Run XHS Crawler")
    parser.add_argument("--keyword", type=str, required=True, help="Search keyword")
    args = parser.parse_args()

    # 运行
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(args.keyword))