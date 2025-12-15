import asyncio
import os
import sys
from mcp.server.fastmcp import FastMCP

# ================= 配置区 =================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "image_gen_cli.py")
# 使用统一环境 Python
PYTHON_EXECUTABLE = sys.executable
# =========================================

mcp = FastMCP("XHS Image Generator")

@mcp.tool()
async def generate_images_from_article(article_path: str) -> str:
    """
    Generate Xiaohongshu-style cover and content images based on the generated markdown article.
    
    Args:
        article_path: The absolute path to the generated markdown file (e.g., .../final_post_xxx.md).
    """
    print(f"--- [MCP-Artist] Designing & Generating images for: {os.path.basename(article_path)} ---")

    try:
        if not os.path.exists(article_path):
            return f"❌ Error: Article file not found at {article_path}"

        cmd = [PYTHON_EXECUTABLE, IMAGE_SCRIPT_PATH, "--file", article_path]
        
        print(f"[Debug] Executing: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # 图片生成比较慢，设置较长的超时或实时读取（这里简化为等待）
        stdout, stderr = await process.communicate()
        output = stdout.decode().strip()
        error_output = stderr.decode().strip()

        if process.returncode != 0:
            return f"❌ Image generation failed.\nError:\n{error_output}\nOutput:\n{output}"

        # 提取结果
        if "__IMAGES_START__" in output:
            try:
                images_block = output.split("__IMAGES_START__")[1].split("__IMAGES_END__")[0].strip()
                image_list = images_block.split('\n')
                
                output_dir_info = ""
                if "__OUTPUT_DIR__: " in output:
                    output_dir = output.split("__OUTPUT_DIR__: ")[1].strip()
                    output_dir_info = f"\n📂 图片保存目录: {output_dir}"

                return f"✅ 图片生成完毕！共生成 {len(image_list)} 张。\n{output_dir_info}\n\n图片列表:\n" + "\n".join([f"- {os.path.basename(img)}" for img in image_list])
            except IndexError:
                return f"⚠️ Output parsing error. Raw:\n{output}"
        else:
            return f"⚠️ Script finished but no images returned.\nLast output:\n{output[-500:]}"

    except Exception as e:
        return f"❌ MCP Server Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()