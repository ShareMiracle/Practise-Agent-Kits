# Data Analysis Module (数据审计与评分)

本模块使用大语言模型（Qwen-Plus）对采集到的小红书数据进行深度审计，评估内容的可信度与当前季节的适用性。

## 📁 目录结构
- `pyproject.toml` & `uv.lock`: **环境定义文件**（请将统一环境的这两个文件复制到此目录）。
- `mcp_server.py`: MCP 服务端入口。
- `analyze_data_cli.py`: 数据分析核心脚本。

## 🛠️ 环境复刻 (使用 uv)

本模块使用 `uv` 管理依赖。请确保目录中包含 `pyproject.toml` 和 `uv.lock`，然后在**当前目录下**执行：

1. **同步环境**:
   ```bash
   uv sync
  ```

2.  **激活环境**:
      - macOS/Linux: `source .venv/bin/activate`
      - Windows: `.venv\Scripts\activate`

## 🚀 使用方法

### 1. 命令行运行

```bash
# 需设置 API Key
export QWEN_API_KEY="sk-..."
python analyze_data_cli.py --file "/path/to/crawled_content.json"
```

### 2. MCP 服务配置

建议直接指向本目录下的虚拟环境 Python：

```json
"analysis_server": {
  "command": "<YOUR_PROJECT_PATH>/DataAnalysis/.venv/bin/python",
  "args": ["<YOUR_PROJECT_PATH>/DataAnalysis/mcp_server.py"],
  "env": {
    "QWEN_API_KEY": "sk-your_api_key_here"
  }
}
```

> **配置说明**：
>
>   * `command`: 建议填写你 Python 环境的绝对路径（例如 `/path/to/venv/bin/python`）。
>   * `args`: 请将 `<YOUR_PROJECT_PATH>` 替换为 DataAnalysis 项目的实际绝对路径。
>   * `env`: 可以在此处直接配置 API Key，避免在终端重复设置。

## ⚠️ 注意事项

  * 分析过程调用 LLM 会产生 API 费用，请关注 Token 使用量。
  * 脚本会根据当前系统日期自动判断季节（春/夏/秋/冬），作为评分依据之一。