import os
import json
import time
import re
import argparse
import sys
import logging
import requests
import dashscope
from dashscope import Generation, ImageSynthesis
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# ================= 配置区 =================
# 统一使用 QWEN_API_KEY
# 请确保在环境变量中设置了 QWEN_API_KEY
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
if not QWEN_API_KEY:
    raise ValueError("Environment variable 'QWEN_API_KEY' is not set.")
dashscope.api_key = QWEN_API_KEY

# 字体路径配置
# 获取当前脚本所在目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 使用相对路径 (.ttc)
FONT_BOLD = os.path.join(CURRENT_DIR, "font.ttc") 
FONT_REGULAR = os.path.join(CURRENT_DIR, "font.ttc")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("image_gen.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def read_article_content(file_path):
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def design_image_content(article_content):
    logger.info("Step 1: Designing image content structure...")
    
    system_prompt = """
    你是一位资深的小红书旅游博主。你的任务是根据文章内容，规划一套旅游攻略图片的“设计方案”。
    
    请输出一个 JSON 格式的列表，包含以下字段：
    - `filename`: 文件名（如 00_cover.png, 01_shantang.png）。
    - `visual_scene`: 画面场景描述（如“夜晚的山塘街，红灯笼倒映在河水里”）。
    - `text_content`: 图片上需要出现的文字内容，必须是以下 JSON 结构：
        {
            "title": "主标题（如景点名称）",
            "subtitle": "副标题（可选，如'2025攻略'）",
            "highlights": ["核心卖点1", "核心卖点2", "核心卖点3"]
        }
    - `style_mood`: 风格与氛围（如“古风、静谧、暖色调”）。
    
    **规划要求**：
    1. **封面图**：要有吸引眼球的大标题（如“苏州旅游避雷指南”）和核心亮点列表。
    2. **景点图**：选取文中提到的 2-3 个核心推荐景点各做一张。
    
    **输出示例**:
    [
        {
            "filename": "00_cover.png",
            "visual_scene": "苏州博物馆的几何建筑与平江路的小桥流水拼贴，留白以便排版文字",
            "text_content": {
                "title": "苏州旅游避雷",
                "subtitle": "2025冬季保姆级攻略",
                "highlights": ["山塘夜游", "苏博几何", "西园寺撸猫"]
            },
            "style_mood": "清新淡雅，杂志封面感"
        }
    ]
    """

    user_prompt = f"文章内容如下：\n\n{article_content}"

    try:
        response = Generation.call(
            model="qwen-plus",
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            result_format='message'
        )

        if response.status_code == 200:
            content = response.output.choices[0].message.content
            # 提取 JSON
            match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            json_str = match.group(1) if match else content
            # 清理可能存在的非JSON字符
            json_str = json_str.strip()
            parsed_json = json.loads(json_str)
            logger.info(f"Designed Content: {json.dumps(parsed_json, ensure_ascii=False, indent=2)}")
            return parsed_json
        else:
            logger.error(f"Failed to design content. Code: {response.code}")
            return []
    except Exception as e:
        logger.error(f"Error during design phase: {e}")
        return []

def optimize_prompts(design_plan):
    logger.info("Step 2: Optimizing image generation prompts...")
    
    optimized_list = []
    
    for item in design_plan:
        system_prompt = """
        你是一位精通 AI 绘画的提示词工程师。
        你的任务是将用户的“图片设计方案”转化为一段高质量的、描述精准的**图像生成提示词（Prompt）**。
        
        **关键要求**：
        1. **纯净画面**：提示词中必须明确要求**“不要包含任何文字!!、水印、标题”**（No text, no watermark, clean background）。我们将在后期通过代码添加文字。
        2. **留白构图**：根据文字内容（标题、列表），在画面中预留合适的留白区域（如天空、墙面、水面），以便后期排版文字。
        3. **画面描述**：将场景描述扩充为高画质摄影语言（如“8k分辨率”、“柔和光线”、“景深”、“构图完美”）。
        4. **风格统一**：确保所有提示词都包含“小红书风格”、“精致排版背景”、“美学设计”等关键词。
        5. **直接输出**：只输出最终的 Prompt 文本，不要解释。
        """
        
        user_prompt = f"""
        设计方案如下：
        - 场景：{item['visual_scene']}
        - 风格：{item['style_mood']}
        - 需要预留位置给文字：{json.dumps(item['text_content'], ensure_ascii=False)}
        
        请生成一段用于文生图模型的 Prompt。
        """
        
        try:
            response = Generation.call(
                model="qwen-plus",
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                result_format='message'
            )
            
            if response.status_code == 200:
                final_prompt = response.output.choices[0].message.content
                optimized_list.append({
                    "filename": item['filename'],
                    "prompt": final_prompt,
                    "text_content": item['text_content'] # 传递文字内容给后续步骤
                })
                logger.info(f"  -> Optimized prompt for {item['filename']}")
            else:
                logger.error(f"  -> Failed to optimize {item['filename']}")
                
        except Exception as e:
            logger.error(f"Error optimizing prompt for {item['filename']}: {e}")
            
    return optimized_list

def add_text_overlay(image_path, text_content):
    """
    使用 PIL 在图片上添加文字 (字号适中版)
    """
    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        
        is_cover = "cover" in os.path.basename(image_path).lower()
        
        # ==========================================
        # 🔥 修改点: 调小字号 (Moderate Size)
        # ==========================================
        if is_cover:
            title_size = 120      # 原 200 -> 160
            subtitle_size = 80    # 原 100 -> 80
            highlight_size = 60   # 原 80 -> 60
        else:
            title_size = 110      # 原 140 -> 110
            subtitle_size = 65    # 原 80 -> 65
            highlight_size = 50   # 原 70 -> 50
        
        try:
            # .ttc 必须保留 index 参数 (index=0 通常为常规体)
            font_title = ImageFont.truetype(FONT_BOLD, title_size, index=0)
            font_subtitle = ImageFont.truetype(FONT_BOLD, subtitle_size, index=0)
            font_highlight = ImageFont.truetype(FONT_REGULAR, highlight_size, index=0)
            
            logger.info(f"✅ Loaded custom font: {FONT_BOLD}")
            
        except Exception as e:
            logger.error(f"❌ Font loading failed: {e}. Fallback to default.")
            font_title = ImageFont.load_default()
            font_subtitle = ImageFont.load_default()
            font_highlight = ImageFont.load_default()

        # 添加半透明蒙版以增强文字可读性
        gradient = Image.new('L', (width, height), color=0)
        
        if is_cover:
             for y in range(height):
                if y > height * 0.5:
                    alpha = int((y - height * 0.5) / (height * 0.5) * 190)
                    for x in range(width):
                        gradient.putpixel((x, y), max(gradient.getpixel((x, y)), alpha))
                if y < height * 0.3:
                    alpha = int((height * 0.3 - y) / (height * 0.3) * 110)
                    for x in range(width):
                        gradient.putpixel((x, y), max(gradient.getpixel((x, y)), alpha))
        else:
            for y in range(height):
                if y > height * 0.6:
                    alpha = int((y - height * 0.6) / (height * 0.4) * 200)
                    for x in range(width):
                        gradient.putpixel((x, y), alpha)
        
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay.paste((0, 0, 0, 255), (0, 0), mask=gradient)
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

        # 布局逻辑自动根据字号计算，无需修改
        if is_cover:
            # === 封面布局 (居中) ===
            last_y = height * 0.3
            if "title" in text_content and text_content["title"]:
                text = text_content["title"]
                bbox = draw.textbbox((0, 0), text, font=font_title)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                x = (width - text_w) / 2
                y = height * 0.3
                
                draw.text((x + 5, y + 5), text, font=font_title, fill=(0, 0, 0, 180))
                draw.text((x, y), text, font=font_title, fill=(255, 255, 255, 255))
                
                last_y = y + text_h + 35

            if "subtitle" in text_content and text_content["subtitle"]:
                text = text_content["subtitle"]
                bbox = draw.textbbox((0, 0), text, font=font_subtitle)
                text_w = bbox[2] - bbox[0]
                
                x = (width - text_w) / 2
                y = last_y
                
                draw.text((x + 3, y + 3), text, font=font_subtitle, fill=(0, 0, 0, 180))
                draw.text((x, y), text, font=font_subtitle, fill=(255, 255, 0, 255))
                
            if "highlights" in text_content and text_content["highlights"]:
                highlights = text_content["highlights"]
                current_y = height - 160 
                
                for point in reversed(highlights):
                    text = f"• {point} •" 
                    bbox = draw.textbbox((0, 0), text, font=font_highlight)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                    
                    x = (width - text_w) / 2
                    current_y -= (text_h + 25)
                    
                    draw.text((x + 2, current_y + 2), text, font=font_highlight, fill=(0, 0, 0, 180))
                    draw.text((x, current_y), text, font=font_highlight, fill=(255, 255, 255, 255))

        else:
            # === 普通布局 (左对齐) ===
            margin_left = 80
            margin_bottom = 110
            current_y = height - margin_bottom

            if "highlights" in text_content and text_content["highlights"]:
                highlights = text_content["highlights"]
                for point in reversed(highlights):
                    text = f"• {point}"
                    bbox = draw.textbbox((0, 0), text, font=font_highlight)
                    text_h = bbox[3] - bbox[1]
                    current_y -= (text_h + 25)
                    
                    draw.text((margin_left + 2, current_y + 2), text, font=font_highlight, fill=(0, 0, 0, 180))
                    draw.text((margin_left, current_y), text, font=font_highlight, fill=(255, 255, 255, 255))
                
                current_y -= 40

            if "subtitle" in text_content and text_content["subtitle"]:
                text = text_content["subtitle"]
                bbox = draw.textbbox((0, 0), text, font=font_subtitle)
                text_h = bbox[3] - bbox[1]
                current_y -= (text_h + 25)
                
                draw.text((margin_left + 3, current_y + 3), text, font=font_subtitle, fill=(0, 0, 0, 180))
                draw.text((margin_left, current_y), text, font=font_subtitle, fill=(255, 255, 0, 255))
                
                current_y -= 25

            if "title" in text_content and text_content["title"]:
                text = text_content["title"]
                bbox = draw.textbbox((0, 0), text, font=font_title)
                text_h = bbox[3] - bbox[1]
                current_y -= (text_h + 35)
                
                draw.text((margin_left + 4, current_y + 4), text, font=font_title, fill=(0, 0, 0, 180))
                draw.text((margin_left, current_y), text, font=font_title, fill=(255, 255, 255, 255))

        img = img.convert("RGB")
        img.save(image_path)
        logger.info(f"Text overlay added to {image_path}")

    except Exception as e:
        logger.error(f"Error adding text overlay: {e}")

def generate_images(prompts_list, output_dir):
    logger.info(f"Step 3: Generating {len(prompts_list)} images...")
    generated_files = []
    
    for item in prompts_list:
        filename = item['filename']
        prompt_text = item['prompt']
        text_content = item.get('text_content', {})
        
        # 强制不生成文字的 Prompt
        final_prompt = f"{prompt_text}, no text, no watermark, clean background, 杰作, 最佳画质, 8k"
        
        logger.info(f"Generating {filename}...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                rsp = ImageSynthesis.call(
                    model="qwen-image-plus",
                    prompt=final_prompt,
                    negative_prompt="text, watermark, signature, logo, low quality, blurry, distorted, ugly",
                    size="1328*1328",
                    n=1
                )

                if rsp.status_code == 200:
                    if rsp.output and rsp.output.results:
                        image_url = rsp.output.results[0].url
                        logger.info("  -> Success. Downloading...")
                        
                        img_response = requests.get(image_url)
                        img_response.raise_for_status()
                        
                        file_path = os.path.join(output_dir, filename)
                        with open(file_path, "wb") as f:
                            f.write(img_response.content)
                        logger.info(f"  -> Saved raw image to {file_path}")
                        
                        # === 关键步骤：添加文字覆盖 ===
                        add_text_overlay(file_path, text_content)
                        
                        generated_files.append(file_path)
                        break 
                    else:
                        logger.warning(f"  -> Attempt {attempt+1}: No results. Response: {rsp}")
                else:
                    logger.warning(f"  -> Attempt {attempt+1}: Failed. Code: {rsp.status_code}, Message: {rsp.message}")

            except Exception as e:
                logger.error(f"  -> Attempt {attempt+1}: Error: {e}")
            
            if attempt < max_retries - 1:
                logger.info("  -> Retrying in 5 seconds...")
                time.sleep(5)
            else:
                logger.error(f"  -> Failed to generate {filename} after {max_retries} attempts.")
        
        time.sleep(2)
        
    return generated_files

def main(file_path):
    logger.info(f"🚀 Starting Image Generation Pipeline for: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"Input file not found: {file_path}")
        return

    base_dir = os.path.dirname(file_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(base_dir, f"images_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    content = read_article_content(file_path)
    if not content:
        return

    design_plan = design_image_content(content)
    if not design_plan:
        logger.error("Design plan failed.")
        return

    final_prompts = optimize_prompts(design_plan)
    if not final_prompts:
        logger.error("Prompt optimization failed.")
        return

    generated_files = generate_images(final_prompts, output_dir)
    
    if generated_files:
        print(f"__IMAGES_START__")
        for path in generated_files:
            print(path)
        print(f"__IMAGES_END__")
        print(f"__OUTPUT_DIR__: {output_dir}")
        logger.info("🎉 All images generated successfully!")
    else:
        print("Error: No images were generated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True, help="Path to the markdown article")
    args = parser.parse_args()
    
    main(args.file)