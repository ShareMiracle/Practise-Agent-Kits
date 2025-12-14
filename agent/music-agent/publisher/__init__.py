"""
Publisher module for uploading content to platforms.

Includes:
- Bilibili automated upload with Playwright
- Screen automation utilities
"""

from .bilibili_playwright import publish_to_bilibili

__all__ = [
    'publish_to_bilibili',
]
