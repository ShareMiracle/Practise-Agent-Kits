import asyncio
import os
import sys
# 复用环境里的 mcp 库
from mcp.server.fastmcp import FastMCP

# ================= 配置区 =================
# 1. 获取当前脚本所在目录 (即 /Users/zhouying/agent/DataAnalysis)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 2. 分析脚本的绝对路径
ANALYSIS_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "analyze_data_cli.py")

# 3. 指定 Python 解释器路径
PYTHON_EXECUTABLE = sys.executable
# =========================================

mcp = FastMCP("XHS Data Analyst")

@mcp.tool()
async def analyze_xhs_data(file_path: str) -> str:
    """
    Use Qwen LLM to clean, analyze, and score the credibility of XHS notes.
    
    Args:
        file_path: The absolute path to the JSON file (usually from the crawler).
    """
    print(f"--- [MCP-Analyst] Received task: Analyze '{file_path}' ---")

    try:
        if not os.path.exists(file_path):
            return f"❌ Error: File not found at {file_path}"

        # 构造命令: [python路径, 脚本路径, --file, 文件路径]
        cmd = [PYTHON_EXECUTABLE, ANALYSIS_SCRIPT_PATH, "--file", file_path]
        
        print(f"[Debug] Executing: {' '.join(cmd)}")

        # 创建子进程执行
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=PROJECT_ROOT, # 在 DataAnalysis 目录下执行
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # 等待结果
        stdout, stderr = await process.communicate()
        output = stdout.decode().strip()
        error_output = stderr.decode().strip()

        # 检查是否执行失败
        if process.returncode != 0:
            # 这里的 error_output 通常包含 Traceback，非常有价值
            return f"❌ Analysis failed.\nError details:\n{error_output}\n\nStandard Output:\n{output}"

        # 提取结果路径 (依赖 analyze_data_cli.py 最后打印的标记)
        if "__ANALYSIS_RESULT_START__" in output:
            try:
                result_path = output.split("__ANALYSIS_RESULT_START__")[1].split("__ANALYSIS_RESULT_END__")[0].strip()
                return f"✅ Analysis Complete! File saved to:\n{result_path}"
            except IndexError:
                return f"⚠️ Output parsing error. Raw output:\n{output}"
        else:
            return f"⚠️ Analysis finished but path missing.\nLast output:\n{output[-500:]}"

    except Exception as e:
        return f"❌ MCP Server Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()