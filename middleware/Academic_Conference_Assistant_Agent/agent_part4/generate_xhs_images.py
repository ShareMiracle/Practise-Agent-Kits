from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
import os
import dashscope
from dashscope import ImageSynthesis

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

def build_xhs_four_grid_prompt(
    conference,
    city,
    venue
):
    return f"""
A single square image divided into FOUR EQUAL PANELS (2x2 grid).
Clean borders between panels.

TOP LEFT PANEL:
Exterior of {venue}, a major academic conference venue.
Professional, modern architecture.

TOP RIGHT PANEL:
Academic conference daily schedule.
Timetable on paper or tablet.
Clean, structured, realistic.

BOTTOM LEFT PANEL:
Local food near the conference venue in {city}.
Casual dining, authentic local cuisine.

BOTTOM RIGHT PANEL:
A famous landmark or scenic spot in {city}.
Travel photography style.

GLOBAL TEXT OVERLAY:
At the TOP CENTER of the image, add ONE SINGLE LINE of text:
"SEE YOU IN {city}!"

IMPORTANT:
The text must be EXACTLY:
SEE YOU IN {city}!
Do NOT paraphrase, translate, or change wording.
All capital letters.
Simple sans-serif font.
Clean, minimal, not decorative.

Overall style:
clean, modern, realistic photography
academic conference lifestyle
no cartoon, no illustration
high resolution, square image
"""

def generate_xhs_image(prompt, output_dir):
    api_key = os.getenv("DASHSCOPE_API_KEY")
    os.makedirs(output_dir, exist_ok=True)

    rsp = ImageSynthesis.call(
        api_key=api_key,
        model="qwen-image-plus",
        prompt=prompt,
        n=1,
        size="1328*1328",
        prompt_extend=True,
        watermark=False
    )

    if rsp.status_code != HTTPStatus.OK:
        raise RuntimeError("Image generation failed")

    for result in rsp.output.results:
        file_name = PurePosixPath(
            unquote(urlparse(result.url).path)
        ).parts[-1]

        save_path = os.path.join(output_dir, file_name)
        with open(save_path, "wb+") as f:
            f.write(requests.get(result.url).content)

        return save_path



