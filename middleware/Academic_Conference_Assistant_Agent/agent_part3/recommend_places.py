from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def recommend_restaurants_and_attractions(
    city,
    venue,
    address
):
    prompt = f"""
You are a local travel assistant helping an academic conference attendee.

Conference venue:
{venue}, {address}

City:
{city}

Task:
Recommend:
1. 3–5 restaurants near the venue (walking distance preferred)
2. 3–5 local attractions suitable for short visits after conference sessions

Audience:
- Academic researcher
- Limited free time
- Prefers convenient, representative local experiences

Output STRICT JSON with fields:
restaurants (list of name, type, reason)
attractions (list of name, type, reason)

Do not include any extra text.
"""

    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "You are a helpful local guide."},
            {"role": "user", "content": prompt}
        ],
        extra_body={
            "enable_search": True
        }
    )

    return completion.choices[0].message.content
