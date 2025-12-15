# Content Writing Module (文案生成)

本模块基于审计后的数据，模拟“人间清醒”博主人设，自动生成符合当季特色的小红书文案（JSON格式）。

## 📁 目录结构
- `pyproject.toml` & `uv.lock`: **环境定义文件**（请将统一环境的这两个文件复制到此目录）。
- `mcp_server.py`: MCP 服务端入口。
- `content_writer_cli.py`: 文案生成核心脚本。

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
python content_writer_cli.py --file "/path/to/audited_data.json" --keyword "主题"
```

### 2. MCP 服务配置

```json
"writer_server": {
  "command": "<YOUR_PROJECT_PATH>/ContentWriting/.venv/bin/python",
  "args": ["<YOUR_PROJECT_PATH>/ContentWriting/mcp_server.py"],
  "env": {
    "QWEN_API_KEY": "sk-your_api_key_here"
  }
}
```
