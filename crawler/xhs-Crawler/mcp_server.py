import asyncio
import os
import sys
# 这里导入 mcp，使用的是 "mcp-workspace" 环境里的库
from mcp.server.fastmcp import FastMCP

# 获取 mcp_server.py 所在的目录（即 MediaCrawler 项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# 爬虫脚本名称
CRAWLER_SCRIPT_NAME = "run_crawler_cli.py"

mcp = FastMCP("XHS Media Crawler")


@mcp.tool()
async def crawl_xhs_images(keyword: str) -> str:
    """
    Search for XiaoHongShu (RedNote) image notes by keyword.
    """
    print(f"--- [MCP] Delegating task via uv: Crawl keyword '{keyword}' ---")

    try:
        # 指令：uv run run_crawler_cli.py ...
        # 注意：这里调用的 'uv' 会自动查找当前目录（PROJECT_ROOT）下的 pyproject.toml
        # 从而激活 MediaCrawler 自己的独立环境（士兵环境）
        cmd = ["uv", "run", CRAWLER_SCRIPT_NAME, "--keyword", keyword]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=PROJECT_ROOT,  # <--- 关键！强制在 MediaCrawler 目录下执行，确保用到爬虫的依赖
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        output = stdout.decode().strip()
        error_output = stderr.decode().strip()

        if process.returncode != 0:
            return f"❌ Crawler process failed.\nError output:\n{error_output}\n\nStandard output:\n{output}"

        if "__RESULT_PATH_START__" in output:
            try:
                result_part = output.split("__RESULT_PATH_START__")[1].split("__RESULT_PATH_END__")[0]
                return f"✅ Crawling finished!\n{result_part}"
            except IndexError:
                return f"⚠️ Output format parsing failed. Raw output:\n{output}"
        else:
            return f"⚠️ Crawling finished but path marker not found.\nLast output:\n{output[-500:]}"

    except Exception as e:
        return f"❌ MCP Server Error: {str(e)}"


if __name__ == "__main__":
    mcp.run()