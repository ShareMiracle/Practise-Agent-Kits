import os
import argparse
from typing import List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOOD_DIR = os.path.join(BASE_DIR, "food")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "plans")

# 固定竖版画布尺寸（小红书风格 3:4）
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1440


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _load_fonts() -> Tuple[ImageFont.FreeTypeFont, ...]:
    """加载字体"""
    # 粗体字体（用于美食名称）
    candidates_bold = [
        r"C:\Windows\Fonts\msyhbd.ttc",     # 微软雅黑粗体
        r"C:\Windows\Fonts\simhei.ttf",     # 黑体
        r"C:\Windows\Fonts\msyh.ttc",       # 微软雅黑
    ]

    def pick(cands, size):
        for p in cands:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    bold_font = pick(candidates_bold, 48)
    return bold_font,


def _get_text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        return len(text) * 14, getattr(font, "size", 28)


def _find_food_image(food_folder: str) -> Optional[str]:
    """在美食文件夹中查找第一张图片"""
    if not os.path.isdir(food_folder):
        return None
    for fname in os.listdir(food_folder):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return os.path.join(food_folder, fname)
    return None


def generate_food_image(food_dir: str = FOOD_DIR, save_path: Optional[str] = None, city: str = "苏州") -> str:
    """
    生成美食图片拼图
    取food文件夹下的前六个文件夹，每个文件夹里有一个图
    把这六张图均匀的填满整个画布（2列3行）
    在每个美食图片的中间下面位置，用黄色加粗大字写上美食名字
    """
    _ensure_output_dir()
    bold_font, = _load_fonts()

    W = CANVAS_WIDTH
    H = CANVAS_HEIGHT
    
    # 获取前6个美食文件夹
    food_folders = []
    if os.path.isdir(food_dir):
        for d in sorted(os.listdir(food_dir)):
            folder_path = os.path.join(food_dir, d)
            if os.path.isdir(folder_path):
                food_folders.append((d, folder_path))
            if len(food_folders) >= 6:
                break
    
    # 2列3行布局
    cols = 2
    rows = 3
    cell_w = W // cols
    cell_h = H // rows
    
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # 文字颜色（黄色）和描边颜色（深色）
    text_color = (255, 220, 50)
    stroke_color = (80, 60, 0)
    
    for idx, (food_name, folder_path) in enumerate(food_folders):
        if idx >= 6:
            break
        
        # 计算当前格子位置
        col = idx % cols
        row = idx // cols
        cell_x = col * cell_w
        cell_y = row * cell_h
        
        # 查找并加载图片
        food_img_path = _find_food_image(folder_path)
        if food_img_path and os.path.exists(food_img_path):
            try:
                food_img = Image.open(food_img_path).convert("RGB")
                
                # 等比缩放填充整个格子
                img_ratio = food_img.width / food_img.height
                cell_ratio = cell_w / cell_h
                
                if img_ratio > cell_ratio:
                    # 图片更宽，按高度缩放
                    new_h = cell_h
                    new_w = int(new_h * img_ratio)
                else:
                    # 图片更高，按宽度缩放
                    new_w = cell_w
                    new_h = int(new_w / img_ratio)
                
                food_img = food_img.resize((new_w, new_h), Image.LANCZOS)
                
                # 居中裁剪
                left = (new_w - cell_w) // 2
                top = (new_h - cell_h) // 2
                food_img = food_img.crop((left, top, left + cell_w, top + cell_h))
                
                # 粘贴到画布
                img.paste(food_img, (cell_x, cell_y))
                
            except Exception as e:
                # 如果图片加载失败，填充灰色
                draw.rectangle([cell_x, cell_y, cell_x + cell_w, cell_y + cell_h], fill=(200, 200, 200))
        else:
            # 没有图片，填充灰色
            draw.rectangle([cell_x, cell_y, cell_x + cell_w, cell_y + cell_h], fill=(200, 200, 200))
        
        # 在图片中间下方位置绘制美食名称
        text_w, text_h = _get_text_size(draw, food_name, bold_font)
        text_x = cell_x + (cell_w - text_w) // 2
        text_y = cell_y + cell_h - text_h - 40  # 距离底部40像素
        
        # 绘制文字描边（让文字在图片上更清晰）
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((text_x + dx, text_y + dy), food_name, fill=stroke_color, font=bold_font)
        
        # 绘制黄色文字
        draw.text((text_x, text_y), food_name, fill=text_color, font=bold_font)
    
    # 保存
    if not save_path:
        save_path = os.path.join(OUTPUT_DIR, f"{city}_food.png")
    img.save(save_path)
    return save_path


def draw_food(food_dir: str = FOOD_DIR, city: str = "苏州"):
    """
    生成美食拼图
    """
    parser = argparse.ArgumentParser(description="生成美食拼图")
    parser.add_argument("--food", "-f", type=str, default=food_dir,
                        help="美食图片文件夹路径")
    parser.add_argument("--city", "-c", type=str, default=city,
                        help="城市名称")
    
    args = parser.parse_args()
    
    out = generate_food_image(food_dir=args.food, city=args.city)
    print(f"Generated: {out}")


if __name__ == "__main__":
    draw_food()
