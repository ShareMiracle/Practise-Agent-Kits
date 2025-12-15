# MediaCrawler Module (小红书数据采集)

本项目基于 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 进行二次开发，用于抓取小红书指定关键词的笔记内容及评论数据，并支持 MCP 协议调用。

## 📁 目录结构
- `mcp_server.py`: MCP 服务端入口。**注意：此文件需运行在安装了 `mcp` 的环境中**。
- `run_crawler_cli.py`: 爬虫命令行入口。**注意：此文件需运行在 MediaCrawler 原生环境中**。
- `client.py` & `core.py`: 核心爬虫逻辑修改版（用于替换原仓库文件）。

## ⚙️ 运行机制说明 (重要)

由于 `MediaCrawler` 依赖较为复杂，直接安装 `mcp` 会导致依赖冲突。因此本项目采用 **“双环境”** 策略：

1.  **MCP 宿主环境**：运行 `mcp_server.py`，负责与 Claude 建立连接。需要安装 `mcp` 包。
2.  **爬虫执行环境**：通过 `uv` 管理（或原项目的 venv），负责执行具体的 `run_crawler_cli.py` 任务。

**`mcp_server.py` 会通过子进程调用 `uv run ...` 来触发爬虫，因此请确保本机已安装 `uv` 工具。**

## 🛠️ 安装与配置

### 1. 部署 MediaCrawler
请执行以下命令初始化爬虫本体：

```bash
# 1. 克隆原仓库
git clone [https://github.com/NanmiCoder/MediaCrawler.git](https://github.com/NanmiCoder/MediaCrawler.git)
cd MediaCrawler

# 2. 部署核心代码
# 将提交包中的 run_crawler_cli.py 和 mcp_server.py 放入根目录
# 将 client.py 和 core.py 覆盖到 media_platform/xhs/ 目录下

# 3. 初始化爬虫环境 (使用 uv 或 pip)
# 建议直接在 MediaCrawler 目录下运行 uv sync (如果原项目支持) 或手动安装
pip install -r requirements.txt
playwright install
```

### 2. 准备 MCP 运行环境

你需要一个**独立**的 Python 环境来运行 MCP Server（可以使用通用的 Agent 环境）：

```bash
# 在外部通用的环境里
pip install mcp
```

## 🚀 使用方法

### 1. 命令行调试 (直接测试爬虫)

在 `MediaCrawler` 目录下，使用爬虫环境运行：

```bash
python run_crawler_cli.py --keyword "你的搜索关键词"
```

### 2. MCP 服务配置 (Claude Desktop)

请在配置中指定**安装了 `mcp` 包的那个 Python** 来运行 `mcp_server.py`。

```json
"crawler_server": {
  "command": "/path/to/your/mcp_env/bin/python",
  "args": ["<YOUR_PROJECT_PATH>/MediaCrawler/mcp_server.py"]
}
```

> **配置关键点**：
>
>   * `command`: **必须**填写安装了 `mcp` 库的 Python 解释器绝对路径（例如你统一的 Agent 环境）。
>   * `args`: 指向 MediaCrawler 目录下的 `mcp_server.py`。
>   * 脚本内部会自动调用 `uv run` 来切换到爬虫环境执行任务，请确保 `uv` 命令在 PATH 中可用。

## ⚠️ 免责声明

本项目仅供课程作业演示及学习研究使用。请严格遵守小红书平台的使用条款及 Robots 协议，严禁用于商业用途或大规模非法抓取。

