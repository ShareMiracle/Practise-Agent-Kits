import asyncio
import json
import os
import argparse
import sys
import logging
import traceback
import httpx
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
from tqdm import tqdm

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
        logging.FileHandler("analysis_service.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- 动态获取当前时间 ---
CURRENT_DATE = datetime.now()
month = CURRENT_DATE.month
if month in [3, 4, 5]: CURRENT_SEASON = "春季"
elif month in [6, 7, 8]: CURRENT_SEASON = "夏季"
elif month in [9, 10, 11]: CURRENT_SEASON = "秋季"
else: CURRENT_SEASON = "冬季"

CURRENT_DATE_STR = f"{CURRENT_DATE.strftime('%Y年%m月%d日')} ({CURRENT_SEASON})"

# ==============================================================================
# 升级版 System Prompt：加入【可用指数】逻辑
# ==============================================================================
SYSTEM_PROMPT = f"""
你是一名【高级旅游情报审计员】。你的任务是基于【当前日期: {CURRENT_DATE_STR}】，对博文进行深度审计。

【核心评分维度】

1. **维度一：信息可信度 (Credibility Score) | 0-10分**
   * **定义**：内容是否真实？(针对可用指数为1的项目打分)
   * **扣分**：虚构事实(-2)、严重误导(-2)、过度美化(-1)。回忆录性质不扣分。

2. **维度二：当前可参考性 (Reference Value) | 0-10分**
   * **定义**：对今天出发的游客有多大价值？(针对可用指数为1的项目打分)
   * **扣分**：季节严重错位(-3)、信息滞后(-1)。

【输出格式 JSON】
{{
    "summary": "简短摘要",
    "audit_details": [
        {{
            "claim": "博文原文观点",
            "type": "景点/美食/交通/避雷",
            "Credibility Score": 8,
            "Reference Value": 6,
            "evidence_content": "评论证据",
            "correction": "矫正信息" 
        }}
    ],
    "scores": {{
        "final_availability": 0, // 全文整体可用性，只要有一个关键点可用即为1
        "credibility_score": 8.0,
        "reference_score": 6.0
    }}
}}
"""
# ==============================================================================

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_comments_file(content_path):
    dir_name = os.path.dirname(content_path)
    file_name = os.path.basename(content_path)
    if "contents" not in file_name:
        return None
    comments_name = file_name.replace("contents", "comments")
    comments_path = os.path.join(dir_name, comments_name)
    if os.path.exists(comments_path):
        return comments_path
    return None

def test_connection_at_startup(client):
    try:
        client.chat.completions.create(
            model=MODEL_NAME, messages=[{"role": "user", "content": "Hi"}], max_tokens=1
        )
        return True
    except Exception:
        return False

async def process_single_note(client: OpenAI, note: Dict, comments: List[Dict]):
    note_id = note.get('note_id')
    logger.info(f"正在审计笔记: {note_id}")
    
    # --- 修改开始：构建评论层级结构 ---
    root_comments = []      # 一级评论列表
    replies_map = {}        # 二级评论字典：{parent_id: [reply1, reply2...]}
    
    # 1. 第一遍遍历：根据 parent_comment_id 分组
    for c in comments:
        content = c.get("content", "").strip()
        # 简单过滤过短内容，防止无效字符干扰，但保留层级结构
        if len(content) < 1: continue 
        
        c_id = c.get("comment_id")
        p_id = c.get("parent_comment_id")
        
        # 兼容 parent_comment_id 可能是字符串 "0" 或数字 0 的情况
        if str(p_id) == "0":
            root_comments.append(c)
        else:
            # 记录回复，Key 为父评论 ID
            # 注意：这里确保 p_id 是字符串以便后续查找匹配（视具体json数据类型而定，通常建议统一转str）
            p_id_str = str(p_id)
            if p_id_str not in replies_map:
                replies_map[p_id_str] = []
            replies_map[p_id_str].append(c)
            
    # 2. 第二遍遍历：构建用于 Prompt 的文本字符串
    formatted_lines = []
    
    # 限制处理的主评论数量，防止 Token 溢出 (例如只取前30条热门主评)
    for root in root_comments[:30]: 
        root_content = root.get("content", "").strip()
        root_id = str(root.get("comment_id")) # 转字符串以匹配 map key
        
        # 添加一级评论
        formatted_lines.append(f"- [主评] {root_content}")
        
        # 查找并添加该一级评论下的二级评论
        if root_id in replies_map:
            # 可以限制回复数量，例如每个主评只看前5条回复
            for reply in replies_map[root_id][:5]:
                reply_content = reply.get("content", "").strip()
                formatted_lines.append(f"  -> [回复] {reply_content}")

    comments_str = "\n".join(formatted_lines) or "(无有效评论)"
    # --- 修改结束 ---

    user_prompt = f"""
    【待审计博文】
    标题: {note.get('title', '无标题')}
    发布时间戳: {note.get('time', '未知')}
    内容: {note.get('desc', '无内容')}
    
    【当前基准时间】
    今天是: {CURRENT_DATE_STR}
    
    【用户评论证据库】
    {comments_str}
    
    请严格执行审计。
    **特别注意**：如果评论提到“倒闭了”、“拆了”、“没了”，请务必将 `availability_score` 设为 0。
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result_json = json.loads(response.choices[0].message.content)
        
        result_json["note_id"] = note_id
        result_json["original_title"] = note.get("title")
        result_json["original_link"] = f"https://www.xiaohongshu.com/explore/{note_id}"
        
        return result_json

    except Exception as e:
        logger.error(f"❌ 笔记 {note_id} 失败: {e}")
        return {"note_id": note_id, "error": str(e)}

async def main(content_path):
    logger.info(f"🚀 启动深度审计任务 (当前季节: {CURRENT_SEASON})...")
    
    try:
        client = OpenAI(
            api_key=QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            http_client=httpx.Client(trust_env=False, timeout=120.0)
        )
    except Exception as e:
        logger.critical(f"Client Init Failed: {e}")
        return

    if not test_connection_at_startup(client): return

    if not os.path.exists(content_path):
        logger.error("文件不存在")
        return
        
    notes = load_json(content_path)
    if isinstance(notes, dict): notes = [notes]
    
    comments_map = {}
    comments_path = find_comments_file(content_path)
    if comments_path:
        raw_comments = load_json(comments_path)
        for c in raw_comments:
            nid = c.get("note_id")
            if nid not in comments_map: comments_map[nid] = []
            comments_map[nid].append(c)
    
    results = []
    for note in tqdm(notes, desc="Auditing"): 
        nid = note.get("note_id")
        # 这里的 comments_map.get(nid, []) 已经传递了该 note 下的所有评论
        res = await process_single_note(client, note, comments_map.get(nid, []))
        results.append(res)

    output_dir = os.path.dirname(content_path)
    output_filename = "audited_" + os.path.basename(content_path)
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"__ANALYSIS_RESULT_START__")
    print(output_path)
    print(f"__ANALYSIS_RESULT_END__")
    logger.info(f"结果已保存: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True)
    args = parser.parse_args()
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(args.file))