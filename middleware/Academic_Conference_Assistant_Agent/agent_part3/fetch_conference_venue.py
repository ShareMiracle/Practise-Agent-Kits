from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def fetch_conference_venue(conference, year, city):
    prompt = f"""
You are an assistant helping a researcher plan conference travel.

Task:
Find the main venue of the academic conference below.

Conference: {conference}
Year: {year}
City: {city}

IMPORTANT: NOTE THE YEAR AND THE CITY GIVEN. THE OUTPUT CITY SHOULD BE THE SAME WITH INPUT CITY

Instructions:
- Search the official conference website or reliable sources
- Return factual information only
- Output STRICT JSON with the following fields:
  conference, year, city, venue, address

Do not include explanations.
"""

    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "You are a factual research assistant."},
            {"role": "user", "content": prompt}
        ],
        extra_body={
            "enable_search": True
        }
    )

    return completion.choices[0].message.content
