"""
测试小红书 Cookie 是否有效
"""
import json
from textwrap import shorten

import requests

from config import settings

ENDPOINTS = [
    {
        "name": "用户主页",
        "url": "https://www.xiaohongshu.com/user/profile/me",
        "referer": "https://www.xiaohongshu.com/"
    },
    {
        "name": "Creator 登录状态",
        "url": "https://creator.xiaohongshu.com/api/galaxy/creator/user/state",
        "referer": "https://creator.xiaohongshu.com/"
    },
    {
        "name": "Edith 自己信息",
        "url": "https://edith.xiaohongshu.com/api/sns/web/v1/user/self/info",
        "referer": "https://creator.xiaohongshu.com/"
    }
]


def _build_headers(referer: str) -> dict:
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Cookie': settings.XIAOHONGSHU_COOKIE,
        'Referer': referer,
        'Accept': 'application/json,text/plain,*/*'
    }


def _preview_resp_text(response: requests.Response) -> str:
    try:
        payload = response.json()
        text = json.dumps(payload, ensure_ascii=False)
    except ValueError:
        text = response.text or ""
    return shorten(text.replace('\n', ' '), width=160, placeholder='…')


def test_xiaohongshu_cookie():
    """测试小红书 Cookie 是否有效"""

    if not settings.XIAOHONGSHU_COOKIE:
        print("❌ 未配置 XIAOHONGSHU_COOKIE")
        print("\n请在 .env 文件中配置:")
        print('XIAOHONGSHU_COOKIE="your_cookie_here"')
        return False

    print("🔍 正在测试小红书 Cookie...")

    any_success = False
    for endpoint in ENDPOINTS:
        print(f"\n➡️  尝试访问：{endpoint['name']} ({endpoint['url']})")
        try:
            response = requests.get(
                endpoint['url'],
                headers=_build_headers(endpoint['referer']),
                timeout=12
            )
        except requests.exceptions.Timeout:
            print("  ⚠️  请求超时，可能需检查网络/VPN")
            continue
        except Exception as err:
            print(f"  ❌ 请求失败: {err}")
            continue

        preview = _preview_resp_text(response)
        print(f"  ↪ 状态: {response.status_code}，返回片段: {preview}")

        if response.status_code == 200:
            print("  ✅ 该接口确认 Cookie 有效")
            any_success = True
        elif response.status_code in (401, 403):
            print("  ❌ 该接口已判定未登录/权限不足，请重新获取 Cookie")
        elif response.status_code == 302 and 'location' in response.headers:
            location = response.headers['location']
            print(f"  ⚠️ 被重定向到 {location}（通常表示需要登录）")
        else:
            print("  ⚠️ 状态码异常，接口可能升级或 Cookie 权限不足")

    if any_success:
        print("\n✅ 至少有一个接口返回 200，可以继续使用当前 Cookie")
        return True

    print("\n❌ 所有检测接口均未通过，请重新登录并更新 XIAOHONGSHU_COOKIE")
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("小红书 Cookie 验证工具")
    print("=" * 50)
    test_xiaohongshu_cookie()
    print("=" * 50)
