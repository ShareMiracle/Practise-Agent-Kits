import os
import json
import math
from typing import List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont
import argparse


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAN_JSON = os.path.join(BASE_DIR, "苏州_2days_plan.json")
SPOT_DIR = os.path.join(BASE_DIR, "spot")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "plans")

# 固定竖版画布尺寸（小红书风格 3:4）
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1440


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _load_plan(path: str = PLAN_JSON) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_spot_image(spot_name: str, spot_dir: str = SPOT_DIR) -> Optional[str]:
    """在 spot 目录下查找景点文件夹中的第一张图片"""
    folder = os.path.join(spot_dir, spot_name)
    if not os.path.isdir(folder):
        # 尝试模糊匹配（去掉“历史街区”等后缀）
        for d in os.listdir(spot_dir):
            if spot_name.startswith(d) or d.startswith(spot_name.replace("历史街区", "")):
                folder = os.path.join(spot_dir, d)
                break
    if not os.path.isdir(folder):
        return None
    for fname in os.listdir(folder):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return os.path.join(folder, fname)
    return None


def _load_fonts() -> Tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    """加载标题、副标题、正文、小字体、迷你字体、emoji字体、粗体字体"""
    # 标题：活泼艺术字体
    candidates_title = [
        r"C:\Windows\Fonts\STHUPO.TTF",     # 华文琥珀（活泼）
        r"C:\Windows\Fonts\STCAIYUN.TTF",   # 华文彩云
        r"C:\Windows\Fonts\STXINGKA.TTF",   # 华文行楷
        r"C:\Windows\Fonts\simhei.ttf",
    ]
    # 副标题：活泼圆润字体（避免楷体）
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
        r"C:\Windows\Fonts\NotoColorEmoji.ttf",  # Noto Color Emoji (如果安装了)
    ]
    # 粗体字体
    candidates_bold = [
        r"C:\Windows\Fonts\msyhbd.ttc",     # 微软雅黑粗体
        r"C:\Windows\Fonts\simhei.ttf",     # 黑体（本身较粗）
        r"C:\Windows\Fonts\msyh.ttc",       # 微软雅黑（后备）
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
    body_font = pick(candidates_body, 38)
    small_font = pick(candidates_body, 30)
    mini_font = pick(candidates_body, 26)
    emoji_font = pick(candidates_emoji, 28)
    bold_font = pick(candidates_bold, 30)
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
    # 将文本分割成token：数字时间组合、英文单词、或单个中文字符
    # 匹配：数字时间格式(如9:00、10:30-17:00)、连续数字、英文单词、或单个字符
    tokens = re.findall(r'\d+[:\-]\d+(?:[:\-]\d+)*|\d+|[a-zA-Z]+|.', text)
    
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
            # 如果单个token就超宽，还是要加进去
            cur = token
    if cur:
        lines.append(cur)
    return lines


def _draw_arrow_down(draw: ImageDraw.ImageDraw, cx: int, y_start: int, y_end: int, color: Tuple[int, int, int], width: int = 4):
    """绘制可爱风格的虚线箭头，带圆形装饰"""
    # 绘制虚线
    dash_len = 12
    gap_len = 8
    y = y_start
    while y < y_end - 20:
        end_y = min(y + dash_len, y_end - 20)
        draw.line([(cx, y), (cx, end_y)], fill=color, width=width)
        y += dash_len + gap_len
    
    # 绘制圆形箭头头部（更可爱的风格）
    head_radius = 8
    draw.ellipse([
        cx - head_radius, y_end - head_radius * 2,
        cx + head_radius, y_end
    ], fill=color)
    
    # 小三角指示方向
    draw.polygon([
        (cx, y_end + 6),
        (cx - 8, y_end - 4),
        (cx + 8, y_end - 4),
    ], fill=color)


def _draw_text_with_emoji(draw: ImageDraw.ImageDraw, pos: Tuple[int, int], text: str, 
                          text_font, emoji_font, fill: Tuple[int, int, int]):
    """绘制包含emoji的文本，分别使用不同字体"""
    import re
    x, y = pos
    # 匹配emoji的正则表达式
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F9FF"  # 符号和表情
        "\U00002600-\U000027BF"  # 杂项符号
        "\U0001F600-\U0001F64F"  # 表情符号
        "]+", 
        flags=re.UNICODE
    )
    
    parts = []
    last_end = 0
    for match in emoji_pattern.finditer(text):
        if match.start() > last_end:
            parts.append((text[last_end:match.start()], False))
        parts.append((match.group(), True))
        last_end = match.end()
    if last_end < len(text):
        parts.append((text[last_end:], False))
    
    for part_text, is_emoji in parts:
        font = emoji_font if is_emoji else text_font
        try:
            bbox = draw.textbbox((0, 0), part_text, font=font)
            w = bbox[2] - bbox[0]
        except:
            w = len(part_text) * 14
        draw.text((x, y), part_text, fill=fill, font=font)
        x += w


def generate_travel_image(day_index: int, save_path: Optional[str] = None, 
                          plan_json: str = PLAN_JSON, spot_dir: str = SPOT_DIR) -> str:
    """
    生成固定尺寸竖版旅游攻略图。
    每个景点一行：左侧时间+景点名，中间图片，右侧详细信息。
    景点之间用向下箭头连接，交通信息显示在箭头旁边。
    
    Args:
        day_index: 第几天的行程
        save_path: 保存路径，默认为 output/plans/{city}_day{n}.png
        plan_json: JSON行程文件路径，默认为苏州_2days_plan.json
        spot_dir: 景点图片文件夹路径，默认为 spot/
    """
    _ensure_output_dir()
    plan_data = _load_plan(plan_json)
    city = plan_data.get("city", "城市")
    days = plan_data.get("days", 1)
    title_font, subtitle_font, body_font, small_font, mini_font, emoji_font, bold_font = _load_fonts()

    # 活力配色
    bg_color = (255, 250, 240)           # 暖白/米色背景
    accent_color = (255, 100, 80)        # 活力橙红
    accent2_color = (255, 180, 60)       # 金黄点缀
    title_color = (255, 85, 100)         # 粉红标题
    text_color = (50, 50, 50)
    gray_color = (90, 90, 90)
    light_gray = (160, 160, 160)
    star_color = (255, 200, 50)          # 星星金色

    # 获取当天行程
    timelines = plan_data.get("plans", [])
    day_timeline = None
    for entry in timelines:
        if entry.get("day_index") == day_index:
            day_timeline = entry.get("timeline", [])
            break
    if not day_timeline:
        raise ValueError(f"未找到第{day_index}天的行程")

    # 分离景点和交通
    spots = []
    transits = []
    for i, item in enumerate(day_timeline):
        if "spot_data" in item:
            sd = item["spot_data"]
            spots.append({
                "name": sd.get("name", ""),
                "time_period": item.get("time_period", ""),
                "address": sd.get("address", ""),
                "desc": sd.get("description", ""),
                "rating": sd.get("rating", ""),
                "opentime": sd.get("opentime", ""),
                "times": sd.get("times", ""),
            })
        else:
            transits.append({
                "after_spot_index": len(spots) - 1,
                "mode": item.get("mode", ""),
                "duration": item.get("duration_minutes", 0),
                "desc": item.get("description", ""),
            })

    num_spots = len(spots)

    # 固定画布尺寸
    W = CANVAS_WIDTH
    H = CANVAS_HEIGHT
    margin = 36
    title_area_h = 140

    # 根据景点数量自适应行高和箭头高度
    content_h = H - title_area_h - margin
    if num_spots <= 1:
        spot_row_h = content_h
        arrow_h = 0
    else:
        # 分配：景点行 + (n-1)个箭头区
        arrow_h = 45
        spot_row_h = (content_h - (num_spots - 1) * arrow_h) // num_spots
        spot_row_h = max(spot_row_h, 180)  # 最小行高

    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # === 装饰元素：顶部渐变条 ===
    for i in range(8):
        color_r = 255 - i * 2
        color_g = 100 + i * 10
        color_b = 80 + i * 5
        draw.rectangle([0, i * 2, W, i * 2 + 2], fill=(color_r, color_g, color_b))

    # === 标题 ===
    title_text = f"🌸 {city}{days}日游攻略 🌸"
    # 分开绘制标题（主文字用标题字体，emoji用emoji字体）
    title_main = f"{city}{days}日游攻略"
    tw, th = _get_text_size(draw, title_main, title_font)
    emoji_w = 50  # emoji宽度估算
    total_w = emoji_w + tw + emoji_w
    start_x = (W - total_w) // 2
    # 绘制左侧emoji
    draw.text((start_x, 24), "🌸", fill=title_color, font=emoji_font)
    # 绘制主标题
    draw.text((start_x + emoji_w, 24), title_main, fill=title_color, font=title_font)
    # 绘制右侧emoji
    draw.text((start_x + emoji_w + tw, 24), "🌸", fill=title_color, font=emoji_font)

    # === 副标题（活泼字体）===
    subtitle_main = f"第{day_index}天"
    sw, sh = _get_text_size(draw, subtitle_main, subtitle_font)
    subtitle_total_w = emoji_w + sw + emoji_w
    subtitle_x = (W - subtitle_total_w) // 2
    draw.text((subtitle_x, 24 + th + 8), "✨", fill=accent_color, font=emoji_font)
    draw.text((subtitle_x + emoji_w, 24 + th + 8), subtitle_main, fill=accent_color, font=subtitle_font)
    draw.text((subtitle_x + emoji_w + sw, 24 + th + 8), "✨", fill=accent_color, font=emoji_font)

    # === 景点行 ===
    y = title_area_h
    left_col_w = 220       # 左侧时间+景点名列宽
    img_w = 320            # 图片宽度（加大）
    img_h = min(spot_row_h - 20, 360)
    right_col_x = margin + left_col_w + img_w + 24
    right_col_w = W - right_col_x - margin

    for idx, spot in enumerate(spots):
        row_top = y

        # --- 中间：图片 ---
        img_x = margin + left_col_w
        img_y = row_top + 12
        actual_img_h = min(img_h, spot_row_h - 24)

        # --- 左侧：景点名（垂直居中对齐图片）---
        name_text = spot.get("name", "")
        name_lines = _wrap_text(name_text, body_font, left_col_w - 10, draw)
        name_total_h = len(name_lines[:3]) * 44  # 计算景点名总高度
        # 景点名起始y = 图片中心 - 名字高度的一半
        name_start_y = img_y + (actual_img_h - name_total_h) // 2
        ny = name_start_y
        name_bottom_y = ny
        for line in name_lines[:3]:
            draw.text((margin, ny), line, fill=text_color, font=body_font)
            ny += 44
            name_bottom_y = ny

        # 绘制图片
        spot_img_path = _find_spot_image(name_text, spot_dir)
        if spot_img_path and os.path.exists(spot_img_path):
            try:
                sp = Image.open(spot_img_path).convert("RGB")
                # 等比缩放填充
                sp_ratio = sp.width / sp.height
                target_ratio = img_w / actual_img_h
                if sp_ratio > target_ratio:
                    new_h = actual_img_h
                    new_w = int(new_h * sp_ratio)
                else:
                    new_w = img_w
                    new_h = int(new_w / sp_ratio)
                sp = sp.resize((new_w, new_h), Image.LANCZOS)
                # 居中裁剪
                left = (new_w - img_w) // 2
                top = (new_h - actual_img_h) // 2
                sp = sp.crop((left, top, left + img_w, top + actual_img_h))
                img.paste(sp, (img_x, img_y))
            except Exception:
                draw.text((img_x + 10, img_y + actual_img_h // 2), "无图片", fill=light_gray, font=small_font)
        else:
            draw.text((img_x + 10, img_y + actual_img_h // 2), "无图片", fill=light_gray, font=small_font)

        # --- 右侧：详细信息（与图片垂直居中对齐）---
        line_h = 36
        
        # 预先计算右侧信息总高度
        info_lines_count = 0
        rating = spot.get("rating", "")
        opentime = spot.get("opentime", "")
        times = spot.get("times", "")
        desc_text = spot.get("desc", "")
        
        if rating:
            info_lines_count += 1
        if opentime:
            ot_lines = _wrap_text(f"开放时间：{opentime}", bold_font, right_col_w - 5, draw)
            info_lines_count += min(len(ot_lines), 4)
        if times:
            info_lines_count += 1
        if desc_text:
            desc_lines = _wrap_text(desc_text, small_font, right_col_w - 5, draw)
            max_desc_lines = max(1, (actual_img_h - info_lines_count * 34 - 8) // 34)
            info_lines_count += min(len(desc_lines), max_desc_lines)
        
        # 计算信息总高度，使其垂直居中对齐图片
        info_total_h = info_lines_count * 34
        info_start_y = img_y + (actual_img_h - info_total_h) // 2
        info_y = info_start_y

        # 评分
        if rating:
            # 标题加粗，数值普通字体
            label = "评分："
            draw.text((right_col_x, info_y), label, fill=star_color, font=bold_font)
            label_w, _ = _get_text_size(draw, label, bold_font)
            draw.text((right_col_x + label_w, info_y), str(rating), fill=star_color, font=small_font)
            info_y += 34 + 14  # 增加段落间距

        # 开放时间
        if opentime:
            # 标题单独一行，加粗
            label = "开放时间："
            draw.text((right_col_x, info_y), label, fill=gray_color, font=bold_font)
            info_y += 34
            # 时间内容另起一行，使用完整列宽换行
            ot_lines = _wrap_text(str(opentime), small_font, right_col_w - 5, draw)
            for ol in ot_lines[:3]:
                draw.text((right_col_x, info_y), ol, fill=gray_color, font=small_font)
                info_y += 34
            info_y += 14  # 增加段落间距

        # 建议游玩时间
        if times:
            # 标题加粗，数值普通字体
            label = "游玩时长："
            draw.text((right_col_x, info_y), label, fill=accent_color, font=bold_font)
            label_w, _ = _get_text_size(draw, label, bold_font)
            draw.text((right_col_x + label_w, info_y), f"{times}分钟", fill=accent_color, font=small_font)
            info_y += 34 + 14  # 增加段落间距

        # 描述（自动换行）
        if desc_text:
            desc_lines = _wrap_text(desc_text, small_font, right_col_w - 5, draw)
            max_desc_lines = max(1, (img_y + actual_img_h - info_y) // 34)
            for line in desc_lines[:max_desc_lines]:
                draw.text((right_col_x, info_y), line, fill=gray_color, font=small_font)
                info_y += 34

        y += spot_row_h

        # --- 箭头 + 交通信息 ---
        if idx < num_spots - 1:
            # 箭头上下两端与景点名保持相同间距
            arrow_gap = 40  # 箭头与文字的间距
            arrow_start_y = name_bottom_y + arrow_gap  # 当前景点名下方留间距
            # 计算下一个景点名的起始位置
            next_row_top = y + arrow_h
            next_img_y = next_row_top + 12
            next_actual_img_h = min(img_h, spot_row_h - 24)
            # 下一个景点名起始y（垂直居中对齐图片）
            next_name_start_y = next_img_y + (next_actual_img_h - 44) // 2  # 假设1行高度44
            arrow_end_y = next_name_start_y - arrow_gap  # 箭头末端与下一景点名上方留间距
            arrow_cx = margin + 20  # 箭头放在左侧边缘

            # 查找对应的交通信息
            transit_info = ""
            for t in transits:
                if t.get("after_spot_index") == idx:
                    transit_info = t.get("desc", "") or f"{t.get('mode', '')}：约{t.get('duration', '')}分钟"
                    break

            # 画箭头连接两个景点名
            _draw_arrow_down(draw, arrow_cx, arrow_start_y, arrow_end_y, accent2_color, width=4)

            # 交通文字（箭头右侧，在冒号后换行）
            if transit_info:
                # 在冒号后换行
                if "：" in transit_info:
                    parts = transit_info.split("：", 1)
                    line1 = f"🚗 {parts[0]}："
                    line2 = parts[1] if len(parts) > 1 else ""
                else:
                    line1 = f"🚗 {transit_info}"
                    line2 = ""
                
                text_y = (arrow_start_y + arrow_end_y) // 2 - 20
                _draw_text_with_emoji(draw, (arrow_cx + 16, text_y), line1, small_font, emoji_font, gray_color)
                if line2:
                    draw.text((arrow_cx + 16, text_y + 34), line2, fill=gray_color, font=small_font)

            y += arrow_h

    # === 底部装饰 ===
    for i in range(5):
        color_r = 255 - i * 3
        color_g = 180 + i * 5
        color_b = 60 + i * 10
        draw.rectangle([0, H - 10 + i * 2, W, H - 8 + i * 2], fill=(color_r, color_g, color_b))

    # 保存
    if not save_path:
        save_path = os.path.join(OUTPUT_DIR, f"{city}_day{day_index}.png")
    img.save(save_path)
    return save_path


def draw_plan(plan_dir = "苏州_2days_plan.json", spot_dir = "spot/"):
    
    parser = argparse.ArgumentParser(description="生成旅游攻略图片")
    parser.add_argument("--plan", "-p", type=str, default=plan_dir,
                        help="JSON行程文件路径，默认为苏州_2days_plan.json")
    parser.add_argument("--spot", "-s", type=str, default=spot_dir,
                        help="景点图片文件夹路径，默认为spot/")
    parser.add_argument("--day", "-d", type=int, default=None,
                        help="指定生成第几天的图片，不指定则生成所有天")
    
    args = parser.parse_args()
    
    data = _load_plan(args.plan)
    
    if args.day is not None:
        # 生成指定天的图片
        out = generate_travel_image(args.day, plan_json=args.plan, spot_dir=args.spot)
        print(f"Generated: {out}")
    else:
        # 生成所有天的图片
        for plan in data.get("plans", []):
            idx = plan.get("day_index")
            out = generate_travel_image(idx, plan_json=args.plan, spot_dir=args.spot)
            print(f"Generated: {out}")

if __name__ == "__main__":
    draw_plan(plan_dir = "苏州_2days_plan.json", spot_dir = "spot/")