from mcp.server.fastmcp import FastMCP
import os
import requests
import uuid
import re
from typing import Dict, Any

mcp = FastMCP("Image Generator")

# Nano Banana API Configuration
NANO_BANANA_API_URL = "https://api.acedata.cloud/nano-banana/images"
NANO_BANANA_API_TOKEN = (
    os.environ.get("NANO_BANANA_API_TOKEN", "").strip()
    or os.environ.get("ACEDATA_API_TOKEN", "").strip()
)


def _validate_travel_poster_prompt(prompt: str) -> Dict[str, Any]:
    """Validate that `prompt` matches the strict 6-line format from travel_image_prompt_guide.

    This is intentionally strict to force the model to follow the guide:
    - Exactly 6 non-empty lines
    - No headings/lists/extra sections
    - Final poster text must be English-only (avoid Chinese to reduce garbling)
    - Time ranges must appear in lines 2–4
    - Line 6 must include weather + outfit advice
    """
    if prompt is None:
        return {"ok": False, "errors": ["prompt 不能为空"]}

    raw = str(prompt).strip()
    if not raw:
        return {"ok": False, "errors": ["prompt 不能为空"]}

    if "\n\n" in raw:
        return {"ok": False, "errors": ["prompt 不允许包含空行；必须严格 6 行，每行一个模块"]}

    lines = [line.strip() for line in raw.splitlines()]
    if any(not line for line in lines):
        return {"ok": False, "errors": ["prompt 不允许出现空行；必须严格 6 行"]}
    if len(lines) != 6:
        return {"ok": False, "errors": [f"prompt 必须严格 6 行；当前为 {len(lines)} 行"]}

    forbidden_tokens = ["##", "---", "第一行", "第二行", "第三行", "第四行", "第五行", "输出格式", "严禁", "示例", "执行步骤"]
    for token in forbidden_tokens:
        if token in raw:
            return {"ok": False, "errors": [f"prompt 只能是最终六行内容，不能包含说明/标题（检测到：{token}）"]}

    # English-only: reject any CJK characters to avoid Chinese text garbling.
    # (Prompt itself must be English-only; you can still pass `city` in Chinese to the guide.)
    if re.search(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]", raw):
        return {"ok": False, "errors": ["prompt 必须为英文纯文本（不得包含中文/汉字），以降低海报文字乱码概率"]}

    for idx, line in enumerate(lines, start=1):
        if line.startswith(("-", "•", "*", "1)", "1.", "（1）")):
            return {"ok": False, "errors": [f"第 {idx} 行疑似列表/项目符号开头；最终输出必须为纯文本六行"]}
        if "XX" in line or "xxx" in line.lower():
            return {"ok": False, "errors": [f"第 {idx} 行仍包含占位符（如 XX）；请用明确内容填充"]}

    errors: list[str] = []

    # Line 1: title only.
    # User requirement: first line must be a pure English title like “One Day Schedule of Changsha”.
    l1 = lines[0].strip()
    l1_lower = l1.lower()
    if "one day" not in l1_lower and "one-day" not in l1_lower and "1-day" not in l1_lower:
        errors.append("第 1 行必须是英文标题，并包含 'one day/one-day/1-day'（示例：One Day Schedule of Changsha）")
    forbidden_in_title = [
        "morning",
        "afternoon",
        "evening",
        "weather",
        "outfit",
        "8:00",
        "11:00",
        "12:00",
        "15:00",
        "16:00",
        "19:00",
        "infographic",
        "poster",
        "layout",
        "module",
    ]
    if any(tok in l1_lower for tok in forbidden_in_title):
        errors.append("第 1 行只能是标题本身，不要包含分栏说明/时间段/布局指令")

    # Line 2–4: enforce time ranges
    required_time_markers = [
        (2, ["8:00", "11:00"]),
        (3, ["12:00", "15:00"]),
        (4, ["16:00", "19:00"]),
    ]
    for line_no, markers in required_time_markers:
        line = lines[line_no - 1]
        line_lower = line.lower()
        if line_no == 2 and "morning" not in line_lower:
            errors.append("第 2 行必须为 MORNING（英文）模块")
        if line_no == 3 and "afternoon" not in line_lower:
            errors.append("第 3 行必须为 AFTERNOON（英文）模块")
        if line_no == 4 and "evening" not in line_lower:
            errors.append("第 4 行必须为 EVENING（英文）模块")
        if line_no == 6 and "the picture is 5 line sturcture, the first line is title, and 2,3,4 are morning, afternoon, evening. The 5 line is the weather and the outfit suggestion." not in line_lower:
            errors.append("第 6 行必须为 STYLE CONTROL（英文）模块, 添加提示词：‘the picture is 5 line sturcture, the first line is title, and 2,3,4 are morning, afternoon, evening. The 5 line is the weather and the outfit suggestion. Global style (apply to ALL panels): clean travel infographic poster, soft illustration / watercolor feel, subtle paper texture, generous whitespace, well-aligned grid, no handwriting, no warped letters, no garbled text.‘")
        # if any(bad in line_lower for bad in ["noon", "night"]):
        #     errors.append(f"第 {line_no} 行请使用 Morning/Afternoon/Evening，不要使用 noon/night")
        for m in markers:
            if m not in line:
                errors.append(f"第 {line_no} 行必须包含时间 {markers[0]}–{markers[1]}")
                break

    l5 = lines[4].lower()
    if "weather" not in l5:
        errors.append("第 5 行必须包含 weather 信息")
    if "outfit" not in l5 and "wear" not in l5:
        errors.append("第 5 行必须包含 outfit/穿衣建议（用英文表达）")
    
    # if "morning" in l5 or "afternoon" in l5 or "evening" in l5:
    #     errors.append("第 5 行仅写天气与穿搭建议（可带收尾建议），不要再写早上/下午/晚上分栏，同时加上图片风格和清晰字体要求")

    if errors:
        return {"ok": False, "errors": errors}

    return {"ok": True}


@mcp.prompt(
    name='travel_image_prompt_guide',
    description='旅游攻略长图的提示词生成框架（严格六行结构；不要求预算）'
)
def travel_image_prompt_guide(city: str, weather: str = "Sunny 20°C") -> str:
    """返回“严格六行结构”的长图生图 Prompt 生成框架。必须使用英文prompt，必须使用英文，禁止使用中文！

    注意：这是“生成六行最终 Prompt 的框架/要求”，不是最终六行 Prompt 本身。
    """
    # Minimal built-in mapping for common cities used in this repo.
    # If your city isn't listed, pass the English name directly as `city`.
    city_en_map = {
        "长沙": "Changsha",
        "哈尔滨": "Harbin",
        "西安": "Xi'an",
        "北京": "Beijing",
        "上海": "Shanghai",
        "广州": "Guangzhou",
        "深圳": "Shenzhen",
        "成都": "Chengdu",
        "杭州": "Hangzhou",
        "南京": "Nanjing",
        "武汉": "Wuhan",
        "重庆": "Chongqing",
    }
    city_en = city_en_map.get(city.strip(), city.strip())

    return f"""You will create a text prompt for generating a vertical one-day travel infographic poster for {city_en}.

Output rules (VERY STRICT):
- Output EXACTLY 6 lines of plain English text.
- No extra explanations, no bullet points, no empty lines.
- All poster text must be English only (no Chinese/CJK characters).

Line 1 (TITLE ONLY): A clean title text only, e.g. "One Day Schedule of {city_en}" (do NOT add layout instructions or times on this line).
Line 2 (MORNING panel): Must include 8:00–11:00. Layout: put "MORNING 8:00–11:00" at the top-left of the morning panel; put the spot name + one actionable tip at the bottom-right; describe the scene in 15+ English words; typography: crisp, sharp, readable sans-serif.
Line 3 (AFTERNOON panel): Must include 12:00–15:00. Layout: "AFTERNOON 12:00–15:00" top-left; spot name + one actionable tip bottom-right; 15+ English words scene description; crisp readable sans-serif.
Line 4 (EVENING panel): Must include 16:00–19:00. Layout: "EVENING 16:00–19:00" top-left; spot name + one actionable tip bottom-right; 15+ English words with golden hour / sunset mood; crisp readable sans-serif.
Line 5 (WEATHER & OUTFIT panel): Must include Weather: "{weather}" and clear outfit advice in English (e.g. "Light jacket + comfortable sneakers"); optional simple icon-like weather/outfit note; add one short route wrap-up tip (return / snack / indoor backup). Typography must look like vector print: sharp, high-contrast, no blur, no distortion.
Line 6 (STYLE CONTROL): Must in English (e.g. "Light jacket + comfortable sneakers"); optional simple icon-like weather/outfit note; add one short route wrap-up tip (return / snack / indoor backup). Typography must look like vector print: sharp, high-contrast, no blur, no distortion.

Global style (apply to ALL panels): clean travel infographic poster, soft illustration / watercolor feel, subtle paper texture, generous whitespace, well-aligned grid, no handwriting, no warped letters, no garbled text.
"""


@mcp.tool(
    name='generate_image_nano_banana',
    description='使用 Nano Banana API 生成图片（强制：prompt 必须为 travel_image_prompt_guide 的最终六行格式；不要求门票/预算）。若 prompt 不合格，可传 city/weather 获取框架并按其重写后再调用。'
)
def generate_image_nano_banana(
    prompt: str = "",
    city: str = "",
    weather: str = "Sunny 20°C",
    negative_prompt: str = "",
    num_images: int = 1,
    width: int = 1024,
    height: int = 1024
) -> Dict[str, Any]:
    """
    使用 Nano Banana API 生成图片
    
    参数:
        prompt: 图片描述 prompt（必须为 travel_image_prompt_guide）
        city: 可选；当 prompt 为空/不合格时，用于返回 travel_image_prompt_guide 框架，帮助你重写 prompt
        weather: 可选；同上，用于生成框架中的天气字段
        negative_prompt: 负向提示词
        num_images: 生成图片数量 (默认 1)
        width: 图片宽度 (默认 1024)
        height: 图片高度 (默认 1024)
    
    返回:
        API 响应结果，包含图片 URL 或任务信息
    """
    validation = _validate_travel_poster_prompt(prompt)
    if not validation.get("ok"):
        guide = None
        if city.strip():
            guide = travel_image_prompt_guide(city=city.strip(), weather=weather)

        return {
            "success": False,
            "message": "prompt 未通过强制校验：必须使用 travel_image_prompt_guide 的最终六行格式（严格六行、无标题/无空行/含时间段与天气穿搭）。",
            "errors": validation.get("errors", []),
            "how_to_fix": [
                "用 travel_image_prompt_guide(city, weather) 的要求生成‘最终六行’纯文本",
                "不要任何标题/说明/空行/列表符号",
                "重写后再调用 generate_image_nano_banana(prompt=最终六行)",
            ],
            "guide": guide,
        }

    token = NANO_BANANA_API_TOKEN
    
    if not token:
        return {
            "success": False,
            "message": "错误: 未找到 API Token。请设置环境变量 NANO_BANANA_API_TOKEN（或 ACEDATA_API_TOKEN）。"
        }
    
    headers = {
        "authorization": f"Bearer {token}",
        "accept": "application/json",
        "content-type": "application/json"
    }
    
    if not negative_prompt:
        negative_prompt = (
            "blurry text, illegible text, garbled text, distorted letters, deformed font, "
            "low resolution, jpeg artifacts, watermark, signature, logo, random symbols, "
            "overlapping text, messy typography, handwriting, chinese characters, hanzi, kanji, "
            "cjk text, non-english text"
        )

    payload = {
        "action": "generate",
        "model": "nano-banana",
        "prompt": prompt,
        "width": width,
        "height": height
    }
    
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
        
    try:
        response = requests.post(NANO_BANANA_API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            trace_id = result.get("trace_id")
            
            # Check for image URL
            image_url = None
            
            if "image_urls" in result and result["image_urls"]:
                image_url = result["image_urls"][0]
            elif "data" in result and isinstance(result["data"], list) and len(result["data"]) > 0:
                first_item = result["data"][0]
                if isinstance(first_item, dict):
                    image_url = first_item.get("image_url") or first_item.get("url")

            if image_url:
                try:
                    # Create directory if not exists
                    save_dir = os.path.join(os.getcwd(), "generated_images")
                    os.makedirs(save_dir, exist_ok=True)
                    
                    # Generate filename
                    filename = f"generated_{uuid.uuid4()}.png"
                    local_path = os.path.join(save_dir, filename)
                    
                    # Download image
                    img_resp = requests.get(image_url, stream=True)
                    if img_resp.status_code == 200:
                        with open(local_path, 'wb') as f:
                            for chunk in img_resp.iter_content(1024):
                                f.write(chunk)
                    else:
                        local_path = None
                except Exception as save_err:
                    print(f"Failed to save image: {save_err}")
                    local_path = None

            return {
                "success": True,
                "data": result,
                "trace_id": trace_id,
                "image_url": image_url,
                "local_path": local_path,
                "message": "图片生成成功" + (f"，已保存至 {local_path}" if local_path else "")
            }
        else:
            return {
                "success": False,
                "message": f"API请求失败: {response.status_code}",
                "error": response.text
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"请求异常: {str(e)}"
        }


if __name__ == "__main__":
    import sys
    
    if "--sse" in sys.argv or os.getenv("MCP_TRANSPORT") == "sse":
        print("🚀 启动 Image Generator MCP 服务器 (SSE模式)")
        print("   服务名称: Image Generator")
        print("   工具数量: 2")
        print("   传输协议: Server-Sent Events (SSE)")
        mcp.run(transport="sse")
    else:
        mcp.run()