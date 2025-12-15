import os
import json
import argparse
from typing import List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAN_JSON = os.path.join(BASE_DIR, "苏州_2days_plan.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "plans")

# 固定竖版画布尺寸（小红书风格 3:4）
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1440


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _load_plan(path: str = PLAN_JSON) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_fonts() -> Tuple[ImageFont.FreeTypeFont, ...]:
    """加载标题、副标题、正文、小字体、迷你字体、emoji字体、粗体字体"""
    # 标题：活泼艺术字体
    candidates_title = [
        r"C:\Windows\Fonts\STHUPO.TTF",     # 华文琥珀（活泼）
        r"C:\Windows\Fonts\STCAIYUN.TTF",   # 华文彩云
        r"C:\Windows\Fonts\STXINGKA.TTF",   # 华文行楷
        r"C:\Windows\Fonts\simhei.ttf",
    ]
    # 副标题：活泼圆润字体
    candidates_subtitle = [
        r"C:\Windows\Fonts\STHUPO.TTF",     # 华文琥珀
        r"C:\Windows\Fonts\SIMYOU.TTF",     # 幼圆
        r"C:\Windows\Fonts\msyh.ttc",       # 微软雅黑
        r"C:\Windows\Fonts\simhei.ttf",
    ]
    # 正文：清晰易读
    candidates_body = [
        r"C:\Windows\Fonts\msyh.ttc",       # 微软雅黑
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    # Emoji字体
    candidates_emoji = [
        r"C:\Windows\Fonts\seguiemj.ttf",   # Segoe UI Emoji
        r"C:\Windows\Fonts\NotoColorEmoji.ttf",
    ]
    # 粗体字体
    candidates_bold = [
        r"C:\Windows\Fonts\msyhbd.ttc",     # 微软雅黑粗体
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
    ]

    def pick(cands, size):
        for p in cands:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    title_font = pick(candidates_title, 68)
    subtitle_font = pick(candidates_subtitle, 44)
    body_font = pick(candidates_body, 36)
    small_font = pick(candidates_body, 28)
    mini_font = pick(candidates_body, 24)
    emoji_font = pick(candidates_emoji, 28)
    bold_font = pick(candidates_bold, 32)
    return title_font, subtitle_font, body_font, small_font, mini_font, emoji_font, bold_font


def _get_text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        return len(text) * 14, getattr(font, "size", 28)


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """智能换行：保持数字、时间、英文单词不被拆开"""
    import re
    tokens = re.findall(r'\d+[:\-\.]\d+(?:[:\-\.]\d+)*|\d+|[a-zA-Z]+|.', text)
    
    lines = []
    cur = ""
    for token in tokens:
        test = cur + token
        w, _ = _get_text_size(draw, test, font)
        if w <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = token
    if cur:
        lines.append(cur)
    return lines


def generate_restaurants_image(plan_json: str = PLAN_JSON, save_path: Optional[str] = None) -> str:
    """
    生成餐馆推荐图片
    """
    _ensure_output_dir()
    plan_data = _load_plan(plan_json)
    city = plan_data.get("city", "城市")
    restaurants = plan_data.get("restaurants", [])
    
    title_font, subtitle_font, body_font, small_font, mini_font, emoji_font, bold_font = _load_fonts()

    # 活力配色
    bg_color = (255, 250, 240)           # 暖白/米色背景
    title_color = (255, 85, 100)         # 粉红标题
    name_color = (230, 90, 60)           # 餐馆名橙红色
    address_color = (100, 100, 100)      # 地址灰色
    desc_color = (80, 80, 80)            # 描述深灰
    food_color = (255, 140, 0)           # 招牌菜橙色
    rating_color = (255, 200, 50)        # 评分金色
    cost_color = (50, 180, 100)          # 价格绿色
    divider_color = (255, 200, 150)      # 分隔线颜色

    W = CANVAS_WIDTH
    H = CANVAS_HEIGHT
    margin = 50
    
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # === 装饰元素：顶部渐变条 ===
    for i in range(8):
        color_r = 255 - i * 2
        color_g = 100 + i * 10
        color_b = 80 + i * 5
        draw.rectangle([0, i * 2, W, i * 2 + 2], fill=(color_r, color_g, color_b))

    # === 标题 ===
    title_main = f"{city}美食推荐"
    tw, th = _get_text_size(draw, title_main, title_font)
    emoji_w = 50
    total_w = emoji_w + tw + emoji_w
    start_x = (W - total_w) // 2
    draw.text((start_x, 30), "🍜", fill=title_color, font=emoji_font)
    draw.text((start_x + emoji_w, 30), title_main, fill=title_color, font=title_font)
    draw.text((start_x + emoji_w + tw, 30), "🍜", fill=title_color, font=emoji_font)

    # === 预计算内容总高度以便居中 ===
    content_w = W - margin * 2
    num_restaurants = len(restaurants)
    
    # 估算每个餐馆高度
    estimated_item_h = 170  # 估算每个餐馆的高度
    total_content_h = num_restaurants * estimated_item_h
    
    # 计算起始y使内容稍微偏上（标题区域后）
    title_area_h = 120
    available_h = H - title_area_h - 30
    # 偏上一些，不完全居中
    start_y = title_area_h + max(0, (available_h - total_content_h) // 3)
    
    y = start_y

    for idx, restaurant in enumerate(restaurants):
        name = restaurant.get("name", "")
        address = restaurant.get("address", "")
        description = restaurant.get("description", "")
        food = restaurant.get("food", "")
        rating = restaurant.get("rating", "")
        cost = restaurant.get("cost", "")

        # 餐馆名（大号粗体，橙红色）
        draw.text((margin, y), f"●  {name}", fill=name_color, font=bold_font)
        y += 42

        # 地址
        if address:
            addr_text = f"地址：{address}"
            draw.text((margin + 20, y), addr_text, fill=address_color, font=small_font)
            y += 34

        # 评分和人均（同一行）
        info_x = margin + 20
        if rating:
            rating_text = f"评分：{rating}分"
            draw.text((info_x, y), rating_text, fill=rating_color, font=small_font)
            rw, _ = _get_text_size(draw, rating_text, small_font)
            info_x += rw + 30
        if cost:
            cost_text = f"人均：¥{cost}"
            draw.text((info_x, y), cost_text, fill=cost_color, font=small_font)
        y += 34

        # 招牌推荐
        if food:
            food_text = f"招牌推荐：{food}"
            food_lines = _wrap_text(food_text, small_font, content_w - 40, draw)
            for line in food_lines[:2]:
                draw.text((margin + 20, y), line, fill=food_color, font=small_font)
                y += 32

        # 描述
        if description:
            desc_lines = _wrap_text(description, mini_font, content_w - 40, draw)
            for line in desc_lines[:2]:
                draw.text((margin + 20, y), line, fill=desc_color, font=mini_font)
                y += 30

        # 分隔线（最后一个不画）
        if idx < num_restaurants - 1:
            y += 10
            draw.line([(margin + 20, y), (W - margin - 20, y)], fill=divider_color, width=2)
            y += 20

    # === 底部装饰 ===
    for i in range(5):
        color_r = 255 - i * 3
        color_g = 180 + i * 5
        color_b = 60 + i * 10
        draw.rectangle([0, H - 10 + i * 2, W, H - 8 + i * 2], fill=(color_r, color_g, color_b))

    # 保存
    if not save_path:
        save_path = os.path.join(OUTPUT_DIR, f"{city}_restaurants.png")
    img.save(save_path)
    return save_path


def generate_hotels_image(plan_json: str = PLAN_JSON, save_path: Optional[str] = None) -> str:
    """
    生成住宿推荐图片
    """
    _ensure_output_dir()
    plan_data = _load_plan(plan_json)
    city = plan_data.get("city", "城市")
    hotels = plan_data.get("hotels", [])
    
    title_font, subtitle_font, body_font, small_font, mini_font, emoji_font, bold_font = _load_fonts()

    # 活力配色
    bg_color = (245, 248, 255)           # 淡蓝白背景
    title_color = (70, 130, 200)         # 蓝色标题
    name_color = (60, 120, 180)          # 酒店名蓝色
    address_color = (100, 100, 100)      # 地址灰色
    desc_color = (80, 80, 80)            # 描述深灰
    rating_color = (255, 180, 50)        # 评分金色
    cost_color = (50, 180, 100)          # 价格绿色
    divider_color = (180, 200, 230)      # 分隔线颜色

    W = CANVAS_WIDTH
    H = CANVAS_HEIGHT
    margin = 50
    
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # === 装饰元素：顶部渐变条 ===
    for i in range(8):
        color_r = 100 + i * 5
        color_g = 150 + i * 8
        color_b = 220 - i * 2
        draw.rectangle([0, i * 2, W, i * 2 + 2], fill=(color_r, color_g, color_b))

    # === 标题 ===
    title_main = f"{city}住宿推荐"
    tw, th = _get_text_size(draw, title_main, title_font)
    emoji_w = 50
    total_w = emoji_w + tw + emoji_w
    start_x = (W - total_w) // 2
    draw.text((start_x, 30), "🏨", fill=title_color, font=emoji_font)
    draw.text((start_x + emoji_w, 30), title_main, fill=title_color, font=title_font)
    draw.text((start_x + emoji_w + tw, 30), "🏨", fill=title_color, font=emoji_font)

    # === 预计算内容总高度以便居中 ===
    content_w = W - margin * 2
    num_hotels = len(hotels)
    
    # 估算每个酒店高度
    estimated_item_h = 160
    total_content_h = num_hotels * estimated_item_h
    
    # 计算起始y使内容稍微偏上
    title_area_h = 120
    available_h = H - title_area_h - 30
    # 偏上一些，不完全居中
    start_y = title_area_h + max(0, (available_h - total_content_h) // 3)
    
    y = start_y

    for idx, hotel in enumerate(hotels):
        name = hotel.get("name", "")
        address = hotel.get("address", "")
        description = hotel.get("description", "")
        rating = hotel.get("rating", "")
        cost = hotel.get("cost", "")

        # 酒店名（大号粗体）
        draw.text((margin, y), f"●  {name}", fill=name_color, font=bold_font)
        y += 42

        # 地址
        if address:
            addr_lines = _wrap_text(f"地址：{address}", small_font, content_w - 40, draw)
            for line in addr_lines[:2]:
                draw.text((margin + 20, y), line, fill=address_color, font=small_font)
                y += 32

        # 评分和价格（同一行）
        info_x = margin + 20
        if rating:
            rating_text = f"评分：{rating}"
            draw.text((info_x, y), rating_text, fill=rating_color, font=small_font)
            rw, _ = _get_text_size(draw, rating_text, small_font)
            info_x += rw + 40
        if cost:
            cost_text = f"价格：¥{cost}/晚"
            draw.text((info_x, y), cost_text, fill=cost_color, font=small_font)
        y += 34

        # 描述
        if description:
            desc_lines = _wrap_text(description, mini_font, content_w - 40, draw)
            for line in desc_lines[:2]:
                draw.text((margin + 20, y), line, fill=desc_color, font=mini_font)
                y += 28

        # 分隔线
        if idx < num_hotels - 1:
            y += 8
            draw.line([(margin + 20, y), (W - margin - 20, y)], fill=divider_color, width=2)
            y += 18

    # === 底部装饰 ===
    for i in range(5):
        color_r = 100 + i * 5
        color_g = 150 + i * 8
        color_b = 220 - i * 2
        draw.rectangle([0, H - 10 + i * 2, W, H - 8 + i * 2], fill=(color_r, color_g, color_b))

    # 保存
    if not save_path:
        save_path = os.path.join(OUTPUT_DIR, f"{city}_hotels.png")
    img.save(save_path)
    return save_path


def generate_tips_image(plan_json: str = PLAN_JSON, save_path: Optional[str] = None) -> str:
    """
    生成旅行小贴士图片
    """
    _ensure_output_dir()
    plan_data = _load_plan(plan_json)
    city = plan_data.get("city", "城市")
    tips = plan_data.get("tips", [])
    
    title_font, subtitle_font, body_font, small_font, mini_font, emoji_font, bold_font = _load_fonts()

    # 活力配色（温馨风格）
    bg_color = (255, 252, 245)           # 暖白背景
    title_color = (255, 130, 80)         # 橙色标题
    tip_colors = [
        (230, 80, 80),    # 红
        (255, 150, 50),   # 橙
        (80, 180, 120),   # 绿
        (70, 150, 200),   # 蓝
        (180, 100, 180),  # 紫
    ]
    text_color = (60, 60, 60)
    bullet_color = (255, 180, 100)
    divider_color = (255, 220, 180)

    W = CANVAS_WIDTH
    H = CANVAS_HEIGHT
    margin = 50
    
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # === 装饰元素：顶部渐变条 ===
    for i in range(8):
        color_r = 255 - i * 1
        color_g = 180 + i * 5
        color_b = 100 + i * 8
        draw.rectangle([0, i * 2, W, i * 2 + 2], fill=(color_r, color_g, color_b))

    # === 标题 ===
    title_main = f"{city}旅行小贴士"
    tw, th = _get_text_size(draw, title_main, title_font)
    emoji_w = 50
    total_w = emoji_w + tw + emoji_w
    start_x = (W - total_w) // 2
    draw.text((start_x, 30), "💡", fill=title_color, font=emoji_font)
    draw.text((start_x + emoji_w, 30), title_main, fill=title_color, font=title_font)
    draw.text((start_x + emoji_w + tw, 30), "💡", fill=title_color, font=emoji_font)

    # === 预计算内容总高度以便居中 ===
    content_w = W - margin * 2 - 60
    num_tips = len(tips)
    
    # 预计算每条贴士的实际高度
    tip_heights = []
    for tip in tips:
        tip_lines = _wrap_text(tip, body_font, content_w, draw)
        h = len(tip_lines[:4]) * 44 + 30
        tip_heights.append(max(h, 100))
    
    total_content_h = sum(tip_heights) + (num_tips - 1) * 15  # 加上分隔线间距
    
    # 计算起始y使内容稍微偏上
    title_area_h = 120
    available_h = H - title_area_h - 30
    # 偏上一些，不完全居中
    start_y = title_area_h + max(0, (available_h - total_content_h) // 3)
    
    y = start_y

    for idx, tip in enumerate(tips):
        # 序号圆圈（彩色）
        circle_color = tip_colors[idx % len(tip_colors)]
        circle_x = margin + 25
        circle_y = y + 20
        circle_r = 22
        draw.ellipse([
            circle_x - circle_r, circle_y - circle_r,
            circle_x + circle_r, circle_y + circle_r
        ], fill=circle_color)
        
        # 序号文字
        num_text = str(idx + 1)
        nw, nh = _get_text_size(draw, num_text, bold_font)
        draw.text((circle_x - nw // 2, circle_y - nh // 2 - 2), num_text, fill=(255, 255, 255), font=bold_font)

        # 贴士内容
        tip_lines = _wrap_text(tip, body_font, content_w, draw)
        tip_y = y + 5
        for line in tip_lines[:4]:
            draw.text((margin + 70, tip_y), line, fill=text_color, font=body_font)
            tip_y += 44

        y += tip_heights[idx]

        # 分隔虚线
        if idx < num_tips - 1:
            dash_y = y - 10
            x = margin + 70
            while x < W - margin:
                draw.line([(x, dash_y), (min(x + 15, W - margin), dash_y)], fill=divider_color, width=2)
                x += 25
            y += 15

    # === 底部装饰 ===
    for i in range(5):
        color_r = 255 - i * 1
        color_g = 180 + i * 5
        color_b = 100 + i * 8
        draw.rectangle([0, H - 10 + i * 2, W, H - 8 + i * 2], fill=(color_r, color_g, color_b))

    # 保存
    if not save_path:
        save_path = os.path.join(OUTPUT_DIR, f"{city}_tips.png")
    img.save(save_path)
    return save_path


def draw_text(plan_json: str = PLAN_JSON):
    """
    生成所有文字类图片（餐馆、住宿、小贴士）
    """
    parser = argparse.ArgumentParser(description="生成旅游攻略文字图片")
    parser.add_argument("--plan", "-p", type=str, default=plan_json,
                        help="JSON行程文件路径")
    parser.add_argument("--type", "-t", type=str, default="all",
                        choices=["all", "restaurants", "hotels", "tips"],
                        help="生成类型：all/restaurants/hotels/tips")
    
    args = parser.parse_args()
    
    if args.type == "all" or args.type == "restaurants":
        out = generate_restaurants_image(plan_json=args.plan)
        print(f"Generated: {out}")
    
    if args.type == "all" or args.type == "hotels":
        out = generate_hotels_image(plan_json=args.plan)
        print(f"Generated: {out}")
    
    if args.type == "all" or args.type == "tips":
        out = generate_tips_image(plan_json=args.plan)
        print(f"Generated: {out}")


if __name__ == "__main__":
    draw_text()
