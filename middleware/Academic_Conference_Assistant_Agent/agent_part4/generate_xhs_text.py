from openai import OpenAI
import os
import json

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def generate_xhs_post(
    user_name,
    user_research,
    conference,
    year,
    part1_contacts,
    part2_schedule_summary,
    part3_city_guide
):
    prompt = f"""
你是一名科研博主，准备在小红书分享自己的学术会议参会体验。

请根据以下信息，生成一篇【小红书风格】的参会攻略笔记。

【写作要求】
- 第一人称
- 语气自然、有生活感
- 适合科研人阅读
- 可以使用适量 emoji
- 不要像广告或官方介绍
- 篇幅中等（600-900字）

【作者信息】
姓名：{user_name}
研究方向：{user_research}

【会议信息】
会议：{conference} {year}

【想见的人（coffee chat）】
{json.dumps(part1_contacts, ensure_ascii=False, indent=2)}

【我的参会日程重点】
{part2_schedule_summary}

【城市 & 吃喝玩乐】
{json.dumps(part3_city_guide, ensure_ascii=False, indent=2)}

【内容结构建议】
1. 为什么来这个会议
2. 我的研究方向 & 关注点
3. 参会日程亮点
4. 想认识的人 & networking
5. 会场周边吃喝玩乐
6. 结尾表达：希望认识新朋友，一起 coffee chat / 吃饭 / 逛城市

请直接输出最终的小红书笔记正文。
"""

    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "You are a helpful content creator."},
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content
