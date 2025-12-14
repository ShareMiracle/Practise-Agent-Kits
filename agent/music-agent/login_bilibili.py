#!/usr/bin/env python3
"""
独立的 Bilibili 登录检查和维护程序

用途：
- 定期运行此程序来保持 Bilibili 登录状态
- 如果已登录，直接退出
- 如果未登录，打开浏览器让用户登录，然后退出

使用：
    python login_bilibili.py
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page


# Playwright 持久化用户数据目录（与 bilibili_playwright.py 共用）
USER_DATA_DIR = Path("playwright_bili_profile").resolve()


async def check_and_login():
    """
    检查 Bilibili 登录状态：
    - 如果已登录，打印信息并退出
    - 如果未登录，打开浏览器等待用户手动登录
    """
    print("=" * 60)
    print("Bilibili 登录状态检查器")
    print("=" * 60)
    print()

    async with async_playwright() as p:
        # 使用持久化上下文，保存登录状态
        print(f"📂 使用持久化配置目录: {USER_DATA_DIR}")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,  # 非无头模式，方便用户登录
        )

        page = await browser.new_page()

        print("🔗 正在访问 Bilibili 首页检查登录状态...")
        await page.goto("https://www.bilibili.com/", wait_until="domcontentloaded")

        # 等待页面加载完成
        await page.wait_for_timeout(2000)

        # 检查是否有"登录"按钮
        login_btn = page.locator("text=登录")
        login_btn_count = await login_btn.count()

        if login_btn_count > 0:
            print()
            print("❌ 检测到当前未登录 Bilibili")
            print("=" * 60)
            print("请在浏览器中完成以下操作：")
            print("  1. 点击页面右上角的'登录'按钮")
            print("  2. 使用扫码或密码登录")
            print("  3. 登录成功后，返回终端按回车继续")
            print("=" * 60)
            print()

            input("👉 登录完成后请按回车键继续...")

            # 再次检查登录状态
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            login_btn = page.locator("text=登录")
            login_btn_count_after = await login_btn.count()

            if login_btn_count_after > 0:
                print()
                print("⚠️  仍未检测到登录状态")
                print("   请确保登录成功后重新运行本程序")
                print()
            else:
                print()
                print("✅ 登录成功！")
                print("   登录状态已保存到:", USER_DATA_DIR)
                print("   下次运行主程序时将自动使用此登录状态")
                print()
        else:
            print()
            print("✅ 已检测到登录状态")
            print("   当前登录状态正常，无需重新登录")
            print("   登录信息已保存在:", USER_DATA_DIR)
            print()

        await browser.close()

    print("=" * 60)
    print("程序结束")
    print("=" * 60)


def main():
    """主入口函数"""
    try:
        asyncio.run(check_and_login())
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
