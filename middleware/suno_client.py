# suno_client.py
# 封装 AI Music API (Suno) 的调用逻辑：
# 1. 根据英文描述创建 Suno 任务
# 2. 轮询任务状态
# 3. 下载 mp3 到本地
#
# 对外只暴露一个主函数：
#   generate_music_from_prompt_en(music_prompt_en, title=..., tags=...) -> 本地 mp3 路径

import os
import time
import json
import re
from pathlib import Path
import sys

import requests

# Import config from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_suno_api_key, get_aimusic_base_url

# Load API key from config
API_KEY = get_suno_api_key()

# API base URL
BASE_URL = get_aimusic_base_url()

# 音乐输出目录
OUTPUT_DIR = Path(__file__).parent / "output" / "music"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SunoClientError(Exception):
    pass


def _ensure_api_key():
    if not API_KEY:
        raise SunoClientError(
            "未配置 AI Music API Key，请先设置环境变量 "
            "AIMUSIC_API_KEY / AIMUSIC_API_TOKEN / AIMUSIC_KEY 之一。"
        )


def _slugify(text: str) -> str:
    """把标题变成安全的文件名"""
    text = text.strip()
    if not text:
        return "hakimi_track"
    slug = re.sub(r"[^\w\-]+", "_", text)
    slug = slug.strip("_")
    return slug or "hakimi_track"


# ---------------- 低层封装：创建任务 / 轮询 / 下载 ---------------- #

def _create_suno_task(music_prompt_en: str, title: str, tags=None, make_instrumental: bool = False) -> str:
    """
    根据英文描述创建 Suno 任务（描述模式 + 自动写词）
    返回 task_id
    """
    _ensure_api_key()

    if tags is None:
        tags = ["electronic", "meme", "fast", "cute"]

    url = f"{BASE_URL}/api/v1/suno/create"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        # 描述模式：不自己写歌词，让 Suno 根据描述自动写
        "custom_mode": False,
        "gpt_description_prompt": music_prompt_en,
        "make_instrumental": make_instrumental,
        # 模型版本，你之前测试 OK 的可以用 chirp-v4 / chirp-v5 等
        "mv": "chirp-v4",
        # 如果以后想自己传 tag，可以把下面这一行打开：
        # "tags": ",".join(tags),
    }

    print("[SunoClient] 创建 Suno 任务 ...")
    print("  gpt_description_prompt =", music_prompt_en)

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    print("  HTTP", resp.status_code, resp.text)
    resp.raise_for_status()

    data = resp.json()
    if data.get("message") != "success" or "task_id" not in data:
        raise SunoClientError(f"创建 Suno 任务失败: {data}")

    task_id = data["task_id"]
    print(f"[SunoClient] 任务创建成功，task_id = {task_id}")
    return task_id


def _poll_suno_task(task_id: str, max_wait: int = 360, interval: int = 15) -> dict:
    """
    轮询 Suno 任务状态，直到生成完成或失败。
    返回一个 clip dict（包含 audio_url 等）。
    """
    _ensure_api_key()

    url = f"{BASE_URL}/api/v1/suno/task/{task_id}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }

    start = time.time()
    attempt = 0

    while True:
        elapsed = int(time.time() - start)
        if elapsed > max_wait:
            raise SunoClientError(f"等待 Suno 任务超时（>{max_wait}s），task_id={task_id}")

        attempt += 1
        print(f"[SunoClient] 第 {attempt} 次查询任务状态（已等待 {elapsed}s）...")

        try:
            resp = requests.get(url, headers=headers, timeout=60)
        except requests.exceptions.RequestException as e:
            print("  ⚠️ 网络异常，忽略本次查询：", e)
            time.sleep(interval)
            continue

        print("  HTTP", resp.status_code)

        if resp.status_code == 202:
            print("  任务还在生成中 (202)，继续等待...")
            time.sleep(interval)
            continue

        if resp.status_code != 200:
            raise SunoClientError(f"获取任务状态失败: HTTP {resp.status_code}, body={resp.text}")

        try:
            data = resp.json()
        except Exception:
            raise SunoClientError(f"任务状态返回非 JSON：{resp.text}")

        print("  原始返回：")
        print(json.dumps(data, ensure_ascii=False, indent=2))

        # 按 AI Music API 文档：code=200 且 data 为列表表示有结果
        if data.get("code") == 200 and data.get("data"):
            clip = data["data"][0]
            state = clip.get("state")
            if state == "succeeded":
                print("[SunoClient] 任务完成，clip_id =", clip.get("clip_id"))
                return clip
            if state == "failed":
                raise SunoClientError(f"Suno 任务失败: {clip}")

            print(f"  当前 clip state={state}，继续等待...")
        else:
            print("  还没有成功结果，继续等待...")

        time.sleep(interval)


def _download_audio(clip: dict, filename: str) -> dict:
    """
    根据 clip 里的 audio_url 下载音频到 OUTPUT_DIR
    同时下载封面图片（如果有）
    返回包含音频路径、封面路径、曲名等信息的字典
    """
    audio_url = clip.get("audio_url")
    if not audio_url:
        raise SunoClientError(f"clip 中没有 audio_url 字段: {clip}")

    # 下载音频
    audio_filepath = OUTPUT_DIR / filename
    print(f"[SunoClient] 下载音频: {audio_url}")
    resp = requests.get(audio_url, timeout=300)
    resp.raise_for_status()

    with open(audio_filepath, "wb") as f:
        f.write(resp.content)
    print(f"[SunoClient] 音频已保存到: {audio_filepath}")

    # 下载封面图片（如果有）
    cover_filepath = None
    image_url = clip.get("image_url")
    if image_url:
        # 封面文件名：去掉 .mp3 后缀，加上 _cover.jpg
        cover_filename = filename.rsplit(".", 1)[0] + "_cover.jpg"
        cover_filepath = OUTPUT_DIR / cover_filename

        print(f"[SunoClient] 下载封面图片: {image_url}")
        try:
            resp = requests.get(image_url, timeout=300)
            resp.raise_for_status()
            with open(cover_filepath, "wb") as f:
                f.write(resp.content)
            print(f"[SunoClient] 封面已保存到: {cover_filepath}")
        except Exception as e:
            print(f"⚠️ 下载封面失败: {e}")
            cover_filepath = None

    # 提取其他有用信息
    result = {
        "audio_path": str(audio_filepath),
        "cover_path": str(cover_filepath) if cover_filepath else None,
        "title": clip.get("title"),
        "tags": clip.get("tags"),
        "duration": clip.get("duration"),
        "clip_id": clip.get("clip_id"),
    }

    print(f"\n[SunoClient] === 生成信息 ===")
    print(f"  曲名: {result['title']}")
    print(f"  标签: {result['tags']}")
    print(f"  时长: {result['duration']}秒")
    print(f"  音频: {result['audio_path']}")
    print(f"  封面: {result['cover_path'] or '无'}")
    print("=" * 50 + "\n")

    return result


# ---------------- 对外主函数：一步到位 ---------------- #

def generate_music_from_prompt_en(
    music_prompt_en: str,
    title: str = "Hakimi Meme Track",
    tags=None,
    make_instrumental: bool = False,
    max_wait: int = 360,
    interval: int = 15,
) -> dict:
    """
    对外入口：
    输入：LLM 生成的英文音乐描述（music_prompt_en）
    输出：包含音频路径、封面路径、曲名等信息的字典
    {
        "audio_path": str,  # 音频文件路径
        "cover_path": str | None,  # 封面图片路径（可能为 None）
        "title": str,  # Suno 生成的曲名
        "tags": str,  # 音乐标签
        "duration": str,  # 时长（秒）
        "clip_id": str,  # Suno clip ID
    }
    """
    safe_title = _slugify(title)
    filename = f"{safe_title}.mp3"

    task_id = _create_suno_task(
        music_prompt_en=music_prompt_en,
        title=title,
        tags=tags,
        make_instrumental=make_instrumental,
    )
    clip = _poll_suno_task(task_id, max_wait=max_wait, interval=interval)
    result = _download_audio(clip, filename=filename)
    return result


if __name__ == "__main__":
    # 简单自测：单独跑这个文件也能生成一首歌
    prompt = input(
        "请输入一段英文描述（比如：high energy electronic hakimi meme bgm, fast and catchy）:\n> "
    ).strip()
    if not prompt:
        print("❌ 为空，退出。")
    else:
        try:
            result = generate_music_from_prompt_en(prompt)
            print("✅ 已生成")
            print(f"  音频: {result['audio_path']}")
            print(f"  封面: {result['cover_path']}")
            print(f"  曲名: {result['title']}")
        except Exception as e:
            print("❌ 出错：", e)
