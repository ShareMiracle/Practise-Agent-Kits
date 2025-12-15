import json
import os
import argparse
import sys
import logging
import httpx
import asyncio
from datetime import datetime
from openai import OpenAI

# ================= 配置区 =================
# 请确保在环境变量中设置了 QWEN_API_KEY
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
if not QWEN_API_KEY:
    raise ValueError("Environment variable 'QWEN_API_KEY' is not set.")
MODEL_NAME = "qwen-plus"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("writer_service.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 动态获取时间
CURRENT_DATE = datetime.now()
month = CURRENT_DATE.month
if month in [3, 4, 5]: CURRENT_SEASON = "春季"
elif month in [6, 7, 8]: CURRENT_SEASON = "夏季"
elif month in [9, 10, 11]: CURRENT_SEASON = "秋季"
else: CURRENT_SEASON = "冬季"
CURRENT_DATE_STR = f"{CURRENT_DATE.strftime('%Y年%m月%d日')} ({CURRENT_SEASON})"

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ 读取JSON文件失败: {e}")
        return []

def generate_final_post(client, audited_data, keyword):
    """
    一步生成 JSON 格式的最终文案。
    """
    logger.info("✍️ [AI] 正在生成文案 (JSON格式)...")
    
    if not audited_data:
        logger.warning("⚠️ 数据为空")
        return None
    
    # 数据瘦身，防止 Token 溢出
    minified_data = []
    for item in audited_data:
        if "error" in item: continue
        minified_data.append({
            "title": item.get("original_title", "无标题"),
            "audit_details": item.get("audit_details", []),
            "scores": item.get("scores", {})
        })

    data_context = json.dumps(minified_data, ensure_ascii=False, indent=2)

    # =================================================================
    # 核心 Prompt 构建
    # 逻辑：在保留你原始内容逻辑的基础上，增加 JSON 格式化指令
    # =================================================================
    system_prompt = f"""
    你是一名小红书“人间清醒”旅游博主（人设：犀利、真实、本地通、反矫情）。
    当前时间是：{CURRENT_DATE_STR}。
    
    你拿到了一份关于“{keyword}”的【大数据审计报告】（JSON数据）。
    请基于这份数据，生成一篇《{CURRENT_SEASON}{keyword}保姆级攻略》。

    【🚨 最终输出格式指令 🚨】
    你必须输出一个标准的 **JSON对象**，严格包含以下三个键：
    1. "title": {CURRENT_SEASON}{keyword}保姆级攻略
    2. "content": (字符串) 笔记的正文内容。
    3. "topics": (数组) 包含5-7个相关标签。

    === 关于 "content" 字段的生成逻辑 (绝对不可修改) ===
    【严禁格式】
    1. **禁止使用Markdown语法**：绝对不要出现 #、**、##、- 等符号。
    2. **纯文本输出与排版**：要求纯文本输出，利用“换行”和“Emoji”来区分层级，保持视觉清爽。

    【内容强调！】
    1. 内容必须是基于报告数据生成，不能凭空捏造信息。
    2. 必须结合当前季节（{CURRENT_SEASON}）的特色，突出季节性推荐，不要强调非季节导致的问题（如关门、维修等）！！！
    3. 不要出现打假其他博主的内容，专注于提供有价值的旅游建议。


    【输出结构模板 (用于 content 字段)】
    (请严格按照以下行文顺序，不要随意发挥)

    [开场：2-3句大实话，直接告诉大家{CURRENT_SEASON}去{keyword}到底是不是时候]

    【景点篇】
    ✅ {CURRENT_SEASON}严选
    (景点名)：(推荐理由，突出当季特色)
    ...
    🛑 劝退区 (这个季节去就是大冤种)
    (景点名)：(犀利劝退理由)
    ...

    【美食篇】
    🍜 {CURRENT_SEASON}必吃
    (食物名)：(本地人这个季节才吃的理由)

    📅 过季慎点
    (食物名)：(过季吃了就亏的理由)

    [结尾]两句话总结

    【内容要求】
    - 语气活泼犀利，不要废话。
    - 长度控制在500字左右。
    ===================================================
    """

    user_prompt = f"""
    【审计报告数据】
    {data_context}

    请立即生成 JSON 结果。
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"} # 强制 JSON 输出
        )
        
        result = response.choices[0].message.content
        return json.loads(result)
        
    except Exception as e:
        logger.error(f"❌ 生成失败: {str(e)}")
        return None

def main(file_path, keyword):
    print(f"🚀 [启动] 文案生成流程 | 关键词: {keyword}")
    
    if "sk-" not in QWEN_API_KEY:
        print("❌ 错误: API Key 未配置！")
        return

    client = OpenAI(
        api_key=QWEN_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        http_client=httpx.Client(trust_env=False, timeout=120.0)
    )

    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件不存在 -> {file_path}")
        return

    audited_data = load_json(file_path)
    
    # 一步生成
    final_json = generate_final_post(client, audited_data, keyword)
    
    if final_json:
        output_dir = os.path.dirname(file_path)
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_filename = f"final_post_{keyword}_{date_str}.json"
        output_path = os.path.join(output_dir, output_filename)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ [成功] 文案已生成并保存！")
        print(f"📂 文件路径: {output_path}")
        
        print("-" * 30)
        print(f"Title: {final_json.get('title')}")
        print("-" * 30)

        # 这里的标记是为了方便其他工具抓取路径
        print("__JSON_START__")
        print(output_path)
        print("__JSON_END__")
    else:
        print("❌ [失败] 未能生成文案。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True, help="Audited JSON file path")
    parser.add_argument("--keyword", type=str, default="通用", help="Search keyword")
    args = parser.parse_args()
    
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    main(args.file, args.keyword)