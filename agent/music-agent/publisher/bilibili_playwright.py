# bilibili_playwright.py
# 组合方案：
#   - Playwright：登录 B站 + 打开投稿页 + 填标题/简介/标签
#   - pyautogui + OpenCV：在屏幕上点击“上传视频”按钮，并在文件对话框里输入视频路径

import asyncio
import time
from pathlib import Path
from typing import List
import pyperclip
from playwright.async_api import async_playwright, Page

import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab


# B站投稿页面
UPLOAD_URL = "https://member.bilibili.com/platform/upload/video/frame"

# Playwright 持久化用户数据目录（保存登录态）
USER_DATA_DIR = Path("playwright_bili_profile").resolve()

# 上传按钮模板图片（存放在 templates 目录）
TEMPLATE_PATH = Path("templates/upload_button.png")
TEMPLATE_SUBMIT_PATH = Path("templates/submit_button.png")

def click_submit_button(template_path: str = "templates/submit_button.png", max_scroll: int = 15, scroll_amount: int = -500):
    """
    在当前前台浏览器窗口中：
    1. 反复向下滚动
    2. 每次用模板匹配查找“立即投稿”按钮
    3. 找到就点击

    max_scroll: 最多滚多少次
    scroll_amount: 每次滚轮滚动的量（负数是向下）
    """
    print("🖱️ 开始自动滚轮查找并点击“立即投稿”按钮...")

    template_path = str(Path(template_path).resolve())

    for i in range(max_scroll):
        pos = find_template_on_screen(template_path, threshold=0.85)
        if pos is not None:
            x, y = pos
            print(f"✅ 找到“立即投稿”按钮位置: ({x}, {y})，准备点击...")
            pyautogui.moveTo(x, y, duration=0.4)
            pyautogui.click()
            print("✅ 已点击“立即投稿”按钮。")
            return True

        print(f"  第 {i+1} 次未找到按钮，滚轮向下滚动...")
        pyautogui.scroll(scroll_amount)
        time.sleep(0.7)

    print("❌ 多次滚动后仍未找到“立即投稿”按钮，请手动滚动到底部查看。")
    return False


# ========= 屏幕模板匹配 + 点击上传 ==========

def find_template_on_screen(template_path: str, threshold: float = 0.8):
    """
    在当前屏幕截图中查找模板图片，返回中心坐标 (x, y) 或 None
    """
    from pathlib import Path

    p = Path(template_path)
    print("🔍 模板原始参数:", repr(template_path))
    print("   解析后的绝对路径:", p.resolve())
    print("   文件是否存在:", p.is_file())

    # 截屏
    screenshot = ImageGrab.grab()
    screen_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # 读模板
    template = cv2.imread(str(p), cv2.IMREAD_COLOR)
    if template is None:
        raise FileNotFoundError(f"模板图片读取失败: {p.resolve()}")

    h, w = template.shape[:2]

    res = cv2.matchTemplate(screen_np, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    print(f"[Match] max_val={max_val}")
    if max_val < threshold:
        return None

    top_left = max_loc
    center_x = top_left[0] + w // 2
    center_y = top_left[1] + h // 2
    return center_x, center_y


def click_upload_and_choose_file(video_path: str, template_path: str = "templates/upload_button.png"):
    """
    在当前前台屏幕：
    1. 找到“上传视频”按钮的小图位置
    2. 移动鼠标并点击
    3. 在弹出的文件对话框中粘贴视频路径并回车
    """
    # 计算绝对路径，并检查文件是否存在
    p = Path(video_path).resolve()
    if not p.is_file():
        print(f"❌ 要上传的文件不存在：{p}")
        print("   请确认视频文件生成成功且路径正确。")
        return False

    full_path = str(p)
    print(f"  [Screen] 将输入的完整路径：{full_path}")

    # 给你一点时间确保浏览器在最前、页面加载完
    print("  [Screen] 3 秒后开始在屏幕上查找上传按钮...")
    time.sleep(3)

    pos = find_template_on_screen(template_path, threshold=0.8)
    if pos is None:
        print("❌ 在屏幕上没找到上传按钮模板，可能分辨率/缩放/主题导致匹配失败。")
        return False

    x, y = pos
    print(f"✅ 找到上传按钮位置: ({x}, {y})，准备点击...")
    pyautogui.moveTo(x, y, duration=0.5)
    pyautogui.click()

    # 等文件对话框弹出来，默认焦点一般在“文件名”输入框
    time.sleep(2)

    # 用剪贴板粘贴，避免中文输入问题
    pyperclip.copy(full_path)
    print("  [Screen] 使用 Ctrl+V 粘贴路径到文件名输入框...")
    pyautogui.hotkey("ctrl", "a")   # 全选原内容
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")   # 粘贴完整路径
    time.sleep(0.2)
    pyautogui.press("enter")

    print("✅ 已在文件对话框中选择文件，等待 B站 开始上传...")
    return True


# ========= Playwright 部分：登录 + 填表单 ==========

async def ensure_logged_in(page: Page):
    """确保当前页面已经登录B站。第一次需要你手动登录一次。"""
    await page.goto("https://www.bilibili.com/", wait_until="domcontentloaded")

    login_btn = page.locator("text=登录")
    if await login_btn.count() > 0:
        print("👉 检测到当前未登录，请在弹出的浏览器中手动登录/扫码。")
        input("   登录完成后回车继续 ...")
    else:
        print("✅ 检测到已经登录。")


async def upload_and_submit(
    video_path: str,
    title: str,
    desc: str,
    tags: List[str],
    cover_path: str | None = None,
):
    video_path = str(Path(video_path).resolve())

    if cover_path:
        cover_path = str(Path(cover_path).resolve())

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,  # 一定要有头，这样 pyautogui 才能点到窗口
        )
        page = await browser.new_page()

        # 1. 确保登录
        await ensure_logged_in(page)

        # 2. 打开投稿页
        print("🔗 打开投稿页面 ...")
        await page.goto(UPLOAD_URL, wait_until="domcontentloaded")

        # 3. 把这个页面带到最前（让它成为前台窗口）
        try:
            await page.bring_to_front()
        except Exception:
            pass

        print("📤 准备自动点击上传按钮并选择视频文件 ...")
        ok = click_upload_and_choose_file(video_path, template_path=str(TEMPLATE_PATH))
        if not ok:
            print("❌ 自动点击上传失败，请检查模板图 / 分辨率 / 缩放。")
            input("   你也可以手动上传视频后按回车，我再帮你填标题信息...")
        else:
            # 给点时间让 B站 处理上传队列（你可以视情况调大/调小）
            print("⌛ 等待上传/转码一段时间（示意）...")
            await page.wait_for_timeout(60)

        # 把页面带到前台，方便屏幕点击
        try:
            await page.bring_to_front()
        except Exception:
            pass

        # 直接滚轮到底部匹配“立即投稿”并点击
        ok_submit = click_submit_button(template_path=str(TEMPLATE_SUBMIT_PATH))
        if ok_submit:
            print("✅ 理论上已经点击了“立即投稿”，稍等片刻让 B站 完成提交。")
        else:
            print("⚠️ 自动点击“立即投稿”失败，请在浏览器中手动滚到最下面点击投稿。")

        # 给一点缓冲时间
        await page.wait_for_timeout(10_000)

        await browser.close()


def publish_to_bilibili(
    video_path: str,
    title: str,
    desc: str,
    tags: List[str],
    cover_path: str | None = None,
):
    """同步封装一下，方便在其他脚本里调用"""
    asyncio.run(
        upload_and_submit(
            video_path=video_path,
            title=title,
            desc=desc,
            tags=tags,
            cover_path=cover_path,
        )
    )


if __name__ == "__main__":
    # 简单测试：你先保证 output/video/ 目录下有视频文件 + 模板图片 + 封面图片
    publish_to_bilibili(
        video_path="output/video/hakimi_video.mp4",
        title="【哈基米】自动生成电子BGM 测试稿",
        desc="这是一个测试用的自动投稿示例：\n- 上传按钮通过屏幕模板匹配自动点击\n- 自动填标题/简介/标签\n\n后续你可以手动点投稿按钮。",
        tags=["哈基米", "鬼畜", "AI音乐"],
        cover_path="covers/cover.jpg",
    )
