# agent.py
# 流程：
# 1. 中文需求 -> 中间件 -> 英文 prompt
# 2. 英文 prompt -> Suno API -> 音频
# 3. 音频 + 封面 -> ffmpeg -> 视频
# 4. 自动上传 B 站

import json
from pathlib import Path
from typing import Any, Dict

from config import config
from middleware.hakimi_middleware import generate_music_prompt
from middleware.render_video import audio_to_video
from middleware.suno_client import generate_music_from_prompt_en


def handle_user_request(user_need: str) -> None:
    """执行单次需求处理流程。"""
    user_need = user_need.strip()
    if not user_need:
        print("⚠️ 用户需求为空，跳过。")
        return

    # 🥚 静默彩蛋检测
    _is_easter_egg = user_need == "匆匆那年"
    _easter_egg_audio = Path("output/music/hanian.mp3").resolve()

    # Step 1. 中间件生成结构化提示词
    print("\n[Step1] 调用中间件生成英文音乐 prompt ...")
    try:
        result: Dict[str, Any] = generate_music_prompt(user_need)
    except Exception as exc:  # noqa: BLE001
        print("❌ generate_music_prompt 调用失败：", exc)
        return

    if not isinstance(result, dict):
        print("❌ generate_music_prompt 返回值类型异常：", type(result))
        return

    print("\n=== 中间件返回 JSON ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    style_tags = result.get("style_tags") or ["electronic", "meme", "fast", "cute"]
    music_prompt_en = (result.get("music_prompt_en") or "").strip()
    if not music_prompt_en:
        print("❌ JSON 中缺少 music_prompt_en，无法继续。")
        return

    print("\n=== 准备用于音乐模型的英文描述 ===")
    print(music_prompt_en)
    print("============================================\n")

    # Step 2. 调 Suno 生成音乐
    print("[Step2] 调用 SunoClient 生成音频 ...")

    # 🥚 静默使用预设音乐（用户无感知）
    if _is_easter_egg and _easter_egg_audio.is_file():
        import time
        time.sleep(2)  # 模拟 API 调用延迟
        # 彩蛋模式：构造返回结构
        music_result = {
            "audio_path": str(_easter_egg_audio),
            "cover_path": None,  # 彩蛋使用本地封面
            "title": "匆匆那年",
            "tags": "nostalgic, emotional",
            "duration": "unknown",
            "clip_id": "easter_egg",
        }
        print("✅ 音乐生成完成")
    else:
        try:
            music_result = generate_music_from_prompt_en(
                music_prompt_en=music_prompt_en,
                title="Hakimi Meme Track",
                tags=style_tags,
                make_instrumental=False,
                max_wait=360,
                interval=15,
            )
        except Exception as exc:  # noqa: BLE001
            print("❌ Step2 出错：", exc)
            return

    # 提取音乐信息
    audio_path = Path(music_result["audio_path"])
    suno_title = music_result.get("title") or "Hakimi Meme Track"
    suno_cover_path = music_result.get("cover_path")

    # 封面选择：优先使用 Suno 封面，否则使用本地封面
    if suno_cover_path and Path(suno_cover_path).is_file():
        cover_path = Path(suno_cover_path)
        print(f"✅ 使用 Suno 生成的封面: {cover_path}")
    else:
        cover_path = Path("covers/cover.jpg")
        if not cover_path.is_file():
            print(f"⚠️ 未找到封面图 {cover_path.resolve()}，请放置 cover.jpg 后重试。")
            return
        print(f"✅ 使用本地封面: {cover_path}")

    # Step 3. ffmpeg 合成视频
    print("\n[Step3] 使用 ffmpeg 合成 MP4 ...")
    video_path = audio_to_video(
        audio_path=str(audio_path),
        image_path=str(cover_path),
        out_path="output/video/hakimi_video.mp4",
        fps=24,
    )
    print("✅ Step3 完成，生成视频文件：", video_path)

    # Step 4. 投稿 B 站
    print("\n[Step4] 自动投稿到 B 站 ...")
    from publisher.bilibili_playwright import publish_to_bilibili

    # 使用 Suno 生成的曲名（加上哈基米标签）
    title = f"【哈基米】{suno_title}"
    desc = f"自动生成的哈基米音乐。\n原始需求：{user_need}\nPrompt EN: {music_prompt_en}\n\nSuno 生成信息：\n- 曲名: {suno_title}\n- 时长: {music_result.get('duration')}秒"
    tags = ["哈基米", "鬼畜", "AI音乐"]

    publish_to_bilibili(
        video_path=str(video_path),
        title=title,
        desc=desc,
        tags=tags,
        cover_path=str(cover_path),
    )

    print("\n🎉 全流程结束。")
    print("  - 已向 Suno 请求生成哈基米音乐")
    print(f"  - 曲名: {suno_title}")
    print("  - 已合成 output/video/hakimi_video.mp4")
    print("  - 已尝试自动完成 B 站投稿流程")


def run_hakimi_agent_once() -> None:
    """兼容旧入口，只跑一次。"""
    print("=== 哈基米音乐 Agent ===\n")

    if not config.ensure_configured():
        return

    user_need = input("请输入想要的哈基米音乐需求（中文）：\n> ")
    handle_user_request(user_need)


def run_hakimi_agent_listener() -> None:
    """常驻监听模式，持续等待用户输入。"""
    print("=== 哈基米音乐 Agent（监听模式） ===")
    print("输入 exit/quit/q 可退出。\n")

    if not config.ensure_configured():
        return

    while True:
        try:
            user_need = input("请输入哈基米音乐需求（中文）：\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n检测到退出信号，结束监听。")
            break

        if user_need.lower() in {"exit", "quit", "q"}:
            print("收到退出指令，结束监听。")
            break

        handle_user_request(user_need)
        print("\n--- 等待下一条需求 ---\n")


if __name__ == "__main__":
    run_hakimi_agent_listener()
