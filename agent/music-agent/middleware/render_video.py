# render_video.py

import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import get_ffmpeg_path


def _resolve_ffmpeg_command() -> str:
    """
    Resolve the ffmpeg executable.
    Returns the configured path, directory + binary, or falls back to PATH.
    """
    configured = (get_ffmpeg_path() or "ffmpeg").strip() or "ffmpeg"
    expanded = os.path.expandvars(os.path.expanduser(configured))
    ffmpeg_path = Path(expanded)

    if ffmpeg_path.is_dir():
        binary_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        return str(ffmpeg_path / binary_name)

    if ffmpeg_path.exists() or ffmpeg_path.is_absolute():
        return str(ffmpeg_path)

    return expanded


def audio_to_video(
    audio_path: str,
    image_path: str = "covers/cover.jpg",
    out_path: str = "output/video/hakimi_video.mp4",
    fps: int = 24,
) -> str:
    audio_path = str(Path(audio_path).resolve())
    image_path = str(Path(image_path).resolve())
    out_path = str(Path(out_path).resolve())

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = _resolve_ffmpeg_command()

    cmd = [
        ffmpeg_bin,
        "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-r", str(fps),
        out_path,
    ]

    print(f"[Render] Running ffmpeg (command: {ffmpeg_bin})...")
    subprocess.run(cmd, check=True)
    return out_path


if __name__ == "__main__":
    audio_to_video("output/music/hakimi_aimusicapi_test.mp3", "covers/cover.jpg", "output/video/hakimi_video.mp4")

