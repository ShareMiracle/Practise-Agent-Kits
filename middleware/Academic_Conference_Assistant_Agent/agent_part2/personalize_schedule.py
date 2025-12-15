import os
import argparse
from openai import OpenAI

# ================================
#  Qwen Client
# ================================
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

SCHEDULE_DIR = "agent_part2/schedule_data"


# ================================
#  Load local schedule source
# ================================
def load_schedule_source(conference, year, prefer="html"):
    suffix = "raw.html" if prefer == "html" else "clean.txt"
    path = os.path.join(
        SCHEDULE_DIR, f"{conference}_{year}_{suffix}"
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"❌ 未找到 {path}，请先运行 fetch_schedule.py"
        )

    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ================================
#  Generate personalized schedule
# ================================
def generate_personalized_schedule(
    conference,
    year,
    research_keywords,
    source_format="html"
):
    schedule_source = load_schedule_source(
        conference, year, prefer=source_format
    )

    prompt = f"""
你是一名科研会议参会规划助手。

下面是 {conference} {year} 的会议日程 {source_format.upper()} 源码。
请你直接从中理解会议的日期、时间段、session/活动及其并行关系。

研究兴趣关键词：
{research_keywords}

任务：
1. 对每一天，按时间顺序整理日程
2. 如果同一时间段有多个活动，只推荐最符合研究兴趣的
3. 给出推荐理由

输出格式（严格 JSON）：
{{
  "YYYY-MM-DD": {{
    "HH:MM-HH:MM": [
      {{
        "title": "...",
        "type": "Oral / Poster / Workshop / Tutorial / Social",
        "location": "...",
        "reason": "为什么与研究兴趣相关"
      }}
    ]
  }}
}}

会议日程源码（已截断）：
----------------
{schedule_source[:12000]}
----------------
"""

    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {
                "role": "system",
                "content": (
                    "你擅长从会议官网源码中解析日程，"
                    "并为科研人员制定个性化参会计划。"
                )
            },
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content


# ================================
#  Main (CLI Entry)
# ================================
def main():
    parser = argparse.ArgumentParser(
        description="Generate personalized conference schedule"
    )

    parser.add_argument(
        "--conference",
        type=str,
        required=True,
        help="Conference name, e.g. CVPR"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Conference year, e.g. 2024"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="+",
        required=True,
        help="Research interest keywords"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="html",
        choices=["html", "txt"],
        help="Schedule source format"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="agent_part2/your_personalized_schedule.json",
        help="Output JSON file path"
    )

    args = parser.parse_args()

    print("🧠 正在生成个性化参会日程...")
    schedule_json = generate_personalized_schedule(
        conference=args.conference,
        year=args.year,
        research_keywords=args.keywords,
        source_format=args.source
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(schedule_json)
        print(f"✅ 日程已保存到 {args.output}")
    else:
        print("\n===== Personalized Schedule =====\n")
        print(schedule_json)


if __name__ == "__main__":
    main()
