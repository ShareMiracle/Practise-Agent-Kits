import asyncio
import os
import sys
from typing import List
from mcp.server.fastmcp import FastMCP

# 获取 mcp_server.py 所在的目录（即 xhs-toolkit 项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# 对应的 CLI 脚本名称
PUBLISH_SCRIPT_NAME = "run_publish_cli.py"

mcp = FastMCP("XHS Publisher")

@mcp.tool()
async def publish_xhs_note(json_path: str, image_paths: List[str]) -> str:
    """
    Publish a note to XiaoHongShu via uv environment delegation.
    """
    # 🔥 关键修改 1: 打印到 stderr，不要污染 stdout
    print(f"--- [MCP] Delegating publish task via uv ---", file=sys.stderr)
    print(f"📄 JSON: {os.path.basename(json_path)}", file=sys.stderr)

    try:
        cmd = [
            "uv", "run", PUBLISH_SCRIPT_NAME,
            "--json", json_path,
            "--images", *image_paths
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        output = stdout.decode().strip()
        error_output = stderr.decode().strip()

        # 🔥 关键修改 2: 子进程的日志，也要转发到 stderr
        if output: 
            print(f"[CLI Stdout]:\n{output}", file=sys.stderr)
        if error_output: 
            print(f"[CLI Stderr]:\n{error_output}", file=sys.stderr)

        if process.returncode != 0:
            return f"❌ Publisher process failed.\nError output:\n{error_output}\n\nLog:\n{output}"

        if "__PUBLISH_SUCCESS__" in output:
            link = "Unknown"
            for line in output.split('\n'):
                if line.startswith("Link:"):
                    link = line.replace("Link:", "").strip()
            
            # 只有这里返回的内容，才是通过 MCP 协议传回给 Client 的
            return f"✅ Publishing finished successfully!\n🔗 Link: {link}\n📂 Source: {os.path.basename(json_path)}"
        else:
            return f"⚠️ Process finished but success marker not found.\nOutput:\n{output}"

    except Exception as e:
        return f"❌ MCP Server Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()