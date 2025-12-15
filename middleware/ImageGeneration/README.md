# Image Generation Module (配图设计与生成)

本模块利用 AI 绘图模型（Qwen-Image-Plus）自动设计并生成小红书风格的封面图和配图，并进行文字排版。

## 📁 目录结构
- `pyproject.toml` & `uv.lock`: **环境定义文件**（请将统一环境的这两个文件复制到此目录）。
- `font.ttc`: 字体文件（**必须存在**，否则无法渲染文字）。
- `mcp_server.py`: MCP 服务端入口。
- `image_gen_cli.py`: 图片生成核心脚本。

## 🛠️ 环境复刻 (使用 uv)

请确保目录中包含 `pyproject.toml` 和 `uv.lock`，然后在**当前目录下**执行：

1. **同步环境**:
   ```bash
   uv sync
    ```

## 🚀 使用方法

### 1. 命令行运行

```bash
export QWEN_API_KEY="sk-..."
python image_gen_cli.py --file "/path/to/final_post.json"
```

图片将生成在输入文件所在目录下的 `images_<timestamp>` 文件夹中。

### 2. MCP 服务配置

```json
"image_server": {
  "command": "<YOUR_PROJECT_PATH>/ImageGeneration/.venv/bin/python",
  "args": ["<YOUR_PROJECT_PATH>/ImageGeneration/mcp_server.py"],
  "env": {
    "QWEN_API_KEY": "sk-your_api_key_here"
  }
}
```