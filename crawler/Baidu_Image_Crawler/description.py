from dotenv import load_dotenv
import os
from dataclasses import dataclass
from typing import Optional

import os
import base64
from openai import OpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_community.chat_models.tongyi import ChatTongyi
from pathlib import Path

import base64
import os
from pathlib import Path

def get_image_data_url(image_path: str) -> str:
    """
    将任意格式的图片转换为Data URL
    自动根据扩展名设置正确的MIME类型
    """
    # MIME类型映射
    mime_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
    }
    
    # 获取扩展名并查找MIME类型
    ext = Path(image_path).suffix.lower()
    mime_type = mime_map.get(ext, 'image/jpeg')  # 默认使用jpeg
    
    # 读取并编码图片
    with open(image_path, "rb") as f:
        base64_data = base64.b64encode(f.read()).decode('utf-8')
    
    return f"data:{mime_type};base64,{base64_data}"

def generate_image_description(                     # 隐式参数
    image_path: str,                            # 显式参数
) ->str:
    """
    使用视觉大语言模型解析图片
    
    参数:
    - image_path: 图片的路径
    """

    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    client = OpenAI(
        api_key="sk-c61a24683161407fbf94b80676424cfc",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    completion = client.chat.completions.create(
        model="qwen3-vl-flash", 
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": get_image_data_url(image_path)},
                        # "image_url": {"url": "D:/projects/XHS-Downloader_V2.6_Windows_X64/test.png"}, 
                        # "image_url": {"url": f"data:image/png;base64,{base64_image}"}, 
                        # "image_url": {
                        #     # "url": f"data:image/png;base64,{base64_image}"
                        # PNG图像：  f"data:image/png;base64,{base64_image}"
                        #     # JPEG图像： f"data:image/jpeg;base64,{base64_image}"
                        #     # WEBP图像： f"data:image/webp;base64,{base64_image}"
                    },
                    {"type": "text", "text": "图中描绘的是什么景象?"},
                ],
            },
        ],
    )
    # print(completion.choices[0].message.content)
    return completion.choices[0].message.content



# if __name__ == "__main__":
#     description = generate_image_description(
#         image_path="D:/projects/baidu_downloader/web_spider_image/tmp/1.jpg",
#         city_name="长沙"
#     )
#     print(description)