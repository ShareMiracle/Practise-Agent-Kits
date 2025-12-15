import asyncio
import os
import sys
import json
import argparse
import logging

# ==========================================
# 1. 核心修复：确保能导入 src 模块
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 尝试导入，如果失败则提示
try:
    from src.core.config import XHSConfig
    from src.xiaohongshu.client import create_xhs_client
    from src.xiaohongshu.models import XHSNote
except ImportError as e:
    print(f"❌ [Import Error] 无法导入 src 模块: {e}")
    print(f"   当前路径: {current_dir}")
    print("   请确保 src 文件夹在 xhs-toolkit 目录下")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def publish_task(json_path, image_paths):
    print(f"📂 读取内容文件: {json_path}")
    print(f"🖼️ 接收图片数量: {len(image_paths)}")

    # 1. 读取 JSON 内容
    if not os.path.exists(json_path):
        print(f"❌ 错误: 找不到 JSON 文件: {json_path}")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ JSON 解析失败: {e}")
        return

    # 2. 提取字段
    title = data.get("title", "")
    content = data.get("content", "")
    # 注意：tags 已经在 content 里或者 topics 字段里，这里优先取 topics
    topics = data.get("topics", [])

    if not title or not content:
        print("❌ 错误: JSON 中缺少 title 或 content")
        return

    # 3. 校验图片
    valid_images = []
    for img in image_paths:
        if os.path.exists(img):
            valid_images.append(img)
        else:
            print(f"⚠️ 警告: 图片不存在，跳过: {img}")
    
    if not valid_images:
        print("❌ 错误: 没有有效的图片可发布")
        return

    # 4. 初始化客户端
    print("🔌 正在初始化小红书客户端...")
    try:
        config = XHSConfig()
        client = create_xhs_client(config)
    except Exception as e:
        print(f"❌ 客户端初始化失败: {e}")
        print("   👉 请检查 .env 文件和 xhs_cookies.json 是否存在且有效")
        return

    # 5. 构建笔记
    note = XHSNote(
        title=title,
        content=content,
        images=valid_images,
        topics=topics,
        videos=[]
    )

    print(f"🚀 准备发布: {title}")
    
    try:
        # 6. 执行发布 (这一步会调用 Playwright)
        result = await client.publish_note(note)
        
        if result.success:
            print(f"✅ 发布成功！")
            print(f"🔗 链接: {result.final_url}")
        else:
            print(f"❌ 发布失败: {result.message}")
            
    except Exception as e:
        print(f"❌ 发布过程发生异常: {str(e)}")
        # 常见错误提示
        if "Executable doesn't exist" in str(e):
            print("   👉 错误原因: 缺少浏览器驱动。请运行: playwright install chromium")
        if "Target closed" in str(e):
            print("   👉 错误原因: 浏览器意外关闭。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # 适配 MCP 传入的参数名
    parser.add_argument("--json_path", type=str, required=True, help="Path to the content JSON file")
    parser.add_argument("--images", type=str, nargs='+', required=True, help="List of image paths")
    
    args = parser.parse_args()
    
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(publish_task(args.json_path, args.images))
    except KeyboardInterrupt:
        print("用户取消")
    except Exception as e:
        print(f"❌ 未知致命错误: {e}")
        import traceback
        traceback.print_exc()