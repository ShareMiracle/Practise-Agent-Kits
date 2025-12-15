import asyncio
import os
import sys
from mcp.server.fastmcp import FastMCP

# ================= 配置区 =================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
WRITER_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "content_writer_cli.py")
# 使用统一环境 Python
PYTHON_EXECUTABLE = sys.executable
# =========================================

mcp = FastMCP("XHS Content Writer")

@mcp.tool()
async def generate_travel_guide(audited_file_path: str, keyword: str = "旅游攻略") -> str:
    """
    Generate a Xiaohongshu-style travel guide based on the audited data.
    
    Args:
        audited_file_path: Path to the 'audited_*.json' file.
        keyword: The main topic or keyword (e.g., '苏州旅游', '美食探店'). 
                 The model can generate this based on user intent.
    """
    print(f"--- [MCP-Writer] Generating content for '{keyword}' from '{audited_file_path}' ---")

    try:
        if not os.path.exists(audited_file_path):
            return f"❌ Error: File not found at {audited_file_path}"

        cmd = [PYTHON_EXECUTABLE, WRITER_SCRIPT_PATH, "--file", audited_file_path, "--keyword", keyword]
        
        print(f"[Debug] Executing: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        output = stdout.decode().strip()
        error_output = stderr.decode().strip()

        if process.returncode != 0:
            return f"❌ Generation failed.\nError:\n{error_output}\nOutput:\n{output}"

        # 提取生成的文案
        if "__CONTENT_START__" in output:
            try:
                content = output.split("__CONTENT_START__")[1].split("__CONTENT_END__")[0].strip()
                # 尝试提取文件路径（可选）
                file_path_info = ""
                if "__FILE_PATH__: " in output:
                    saved_path = output.split("__FILE_PATH__: ")[1].strip()
                    file_path_info = f"\n\n(已自动保存至本地: {saved_path})"
                
                return f"✅ 文案生成成功！\n\n{content}{file_path_info}"
            except IndexError:
                return f"⚠️ Output parsing error. Raw:\n{output}"
        else:
            return f"⚠️ Script finished but no content returned.\nLast output:\n{output[-500:]}"

    except Exception as e:
        return f"❌ MCP Server Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()