import os
import json
import pandas as pd
from openai import OpenAI

# ============================
# 初始化 Qwen API
# ============================
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)



# ============================
# 1. 加载会议论文 CSV
# ============================
def load_conference_papers(conference):
    """
    conference: "NeurIPS", "CVPR", "ICLR" 等
    对应文件名格式：NeurIPS_2021_2025_dblp.csv
    """
    filename = f"agent_part1/papers/{conference}_2021_2025_dblp.csv"
    if not os.path.exists(filename):
        raise FileNotFoundError(f"未找到 {filename}")

    df = pd.read_csv(filename)
    return df


# ============================
# 2. 根据关键词筛选论文
# ============================
def filter_papers(df, keywords):
    pattern = '|'.join([kw.lower() for kw in keywords])
    mask = df['title'].str.lower().str.contains(pattern)
    return df[mask]


# ============================
# 3. 根据标题相关性对一作排序
# ============================

def rank_authors_by_relevance(df, keywords, top_k=5):
    """
    返回：
    {
      author_name: {
        "score": int,
        "papers": [ {title, year, conference} ]
      }
    }
    """
    author_info = {}

    for _, row in df.iterrows():
        title = str(row["title"]).lower()
        score = sum(1 for kw in keywords if kw.lower() in title)

        if score == 0:
            continue

        first_author = str(row["authors"]).split(";")[0].strip()

        if first_author not in author_info:
            author_info[first_author] = {
                "score": 0,
                "papers": []
            }

        author_info[first_author]["score"] += score
        author_info[first_author]["papers"].append({
            "title": row["title"],
            "conference": row.get("conference", ""),
            "year": row.get("year_target", "")
        })

    # 排序
    sorted_authors = sorted(
        author_info.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    # 只取 top_k
    return sorted_authors[:top_k]


# ============================
# 4. 使用千问推理：作者主页 + 邮箱
# ============================
def qwen_get_author_info(author_name):
    """让 Qwen 搜索作者主页和邮箱（不依赖外网）"""
    prompt = f"""
你是一名学术信息助手。请根据作者姓名搜索其可能的学术主页与公开邮箱。

作者：{author_name}

请根据：
- 常见学术主页 endwith(github.io)（GitHub，Google Scholar, 机构主页, 个人域名）
- 作者常见邮箱格式（如学校域名）

给出你最合理的搜索结果。

输出 JSON，格式如下：
{{
  "homepage": "...",
  "email": "..."
}}
"""

    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "你是专业学术助手，擅长根据作者姓名检索其主页和邮箱。"},
            {"role": "user", "content": prompt}],
        extra_body={
            "enable_search": True
        }
    )

    content = completion.choices[0].message.content

    try:
        return json.loads(content)
    except:
        return {"homepage": "N/A", "email": "N/A"}


# ============================
# 5. 生成 Coffee Chat 邮件
# ============================
def generate_coffee_chat_email(author_name, author_email, user_name, user_research):
    prompt = f"""
请为下面的学者写一封 Coffee Chat 邮件。

收件人姓名：{author_name}
收件人邮箱：{author_email}
发件人：{user_name}
我的研究方向：{user_research}

要求：
- 自然、礼貌、简短
- 不需要太正式
- 不超过 150 字
"""

    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "你是邮件写作专家，擅长撰写礼貌又自然的英文邮件。"},
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content


# ============================
# 6. 主流程
# ============================
def run_agent_part1(conference, research_keywords, user_name, user_research):
    print("🔍 正在加载会议论文...")
    df = load_conference_papers(conference)

    print("🎯 正在筛选与研究方向相关的论文...")
    df_filtered = filter_papers(df, research_keywords)

    print("📚 相关论文数量：", len(df_filtered))

    print("👥 正在排序最相关的一作作者...")
    print("👥 正在筛选最相关作者（含论文）...")
    author_entries = rank_authors_by_relevance(
        df_filtered, research_keywords, top_k=5
    )

    results = []

    for author, info in author_entries:
        print(f"📡 正在通过大模型获取作者信息：{author}")

        # ① Qwen 推断个人信息
        author_info = qwen_get_author_info(author)
        homepage = author_info.get("homepage", "N/A")
        email = author_info.get("email", "N/A")

        # ② 生成邮件
        email_text = generate_coffee_chat_email(
            author_name=author,
            author_email=email,
            user_name=user_name,
            user_research=user_research
        )

        results.append({
            "author": author,
            "papers": info["papers"],   
            "homepage": homepage,
            "email": email,
            "email_text": email_text
        })

    return results


# ============================
# 7. CLI 调用（可选）
# ============================
# if __name__ == "__main__":
#     conference = "CVPR"      # 修改
#     research_keywords = ["registration", "self-supervised", "3d"]  # 修改
#     user_name = "Siyan"
#     user_research = "self-supervised 3D registration and medical image analysis"

#     output = run_agent_part1(conference, research_keywords, user_name, user_research)

#     # 保存结果
#     with open("agent_part1_output.json", "w", encoding="utf-8") as f:
#         json.dump(output, f, ensure_ascii=False, indent=2)

#     print("\n🎉 任务完成！结果已保存到 agent_part1_output.json\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Agent Part1: Find relevant authors and generate coffee chat emails"
    )

    parser.add_argument(
        "--conference",
        type=str,
        required=True,
        help="Conference name, e.g. CVPR"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="+",
        required=True,
        help="Research keywords, e.g. self-supervised 3d registration"
    )
    parser.add_argument(
        "--user_name",
        type=str,
        required=True,
        help="Your name"
    )
    parser.add_argument(
        "--user_research",
        type=str,
        required=True,
        help="Your research description"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="agent_part1/coffee_chat_email.json",
        help="Output JSON path"
    )

    args = parser.parse_args()

    output = run_agent_part1(
        conference=args.conference,
        research_keywords=args.keywords,
        user_name=args.user_name,
        user_research=args.user_research
    )

    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 任务完成！结果已保存到 {args.output_file}\n")
