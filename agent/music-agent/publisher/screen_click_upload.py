import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab

TEMPLATE_PATH = "templates/upload_button.png"


def find_template_on_screen(template_path: str, threshold: float = 0.8):
    """
    在当前屏幕截图中查找模板图片，返回中心坐标 (x, y) 或 None
    """
    # 截屏（返回PIL Image）
    screenshot = ImageGrab.grab()
    screen_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        raise FileNotFoundError(f"模板图片不存在: {template_path}")

    h, w = template.shape[:2]

    # 模板匹配
    res = cv2.matchTemplate(screen_np, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    print(f"[Match] max_val={max_val}")
    if max_val < threshold:
        return None

    top_left = max_loc
    center_x = top_left[0] + w // 2
    center_y = top_left[1] + h // 2
    return center_x, center_y


def click_upload_and_choose_file(video_path: str):
    # 等你把浏览器切到前台、打开投稿页
    print("请先把浏览器切到前台，并打开B站投稿页。5秒后开始识别上传按钮...")
    time.sleep(5)

    pos = find_template_on_screen(TEMPLATE_PATH, threshold=0.8)
    if pos is None:
        print("❌ 在屏幕上没找到上传按钮模板，可能分辨率/缩放导致匹配失败。")
        return

    x, y = pos
    print(f"✅ 找到上传按钮位置: ({x}, {y})，准备点击...")
    pyautogui.moveTo(x, y, duration=0.5)
    pyautogui.click()

    # 等文件对话框弹出来
    time.sleep(2)

    # 在文件对话框里输入视频路径并回车
    full_path = str(Path(video_path).resolve())
    print(f"在文件对话框中输入路径: {full_path}")
    pyautogui.write(full_path)
    pyautogui.press("enter")

    print("✅ 已在文件对话框中选择文件，等待B站开始上传...")
    # 这里可以再 sleep 一会儿，或者后面用OCR检查状态
    time.sleep(10)


if __name__ == "__main__":
    click_upload_and_choose_file("output/video/hakimi_video.mp4")
