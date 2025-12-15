"""
Middleware module for content generation and processing.

Includes:
- LLM-based prompt generation
- Music generation (Suno API)
- Video rendering
"""

from .hakimi_middleware import generate_music_prompt
from .suno_client import generate_music_from_prompt_en
from .render_video import audio_to_video

__all__ = [
    'generate_music_prompt',
    'generate_music_from_prompt_en',
    'audio_to_video',
]
