
# XHS Toolkit Module (自动化发布)

本模块基于 [xhs-toolkit](https://github.com/aki66938/xhs-toolkit) 二次开发，增强了内容填充稳定性，支持一键发布图文笔记。

## 📁 目录结构
- `mcp_server.py`: MCP 服务端入口。
- `run_publish_cli.py`: 发布命令行入口。
- `src/`: 核心修改代码（覆盖原仓库 src）。

## 🛠️ 安装与配置

### 1. 基础环境
本项目依赖 `xhs-toolkit` 原仓库。

```bash
# 1. 克隆原仓库
git clone [https://github.com/aki66938/xhs-toolkit.git](https://github.com/aki66938/xhs-toolkit.git)
cd xhs-toolkit

# 2. 安装基础依赖
pip install -r requirements.txt
playwright install

# 3. 安装 MCP 依赖
# 注意：若发布工具环境无冲突，可直接在此环境安装 mcp
# 若有冲突，请参考 MediaCrawler 的双环境模式
pip install mcp
````

### 2. 文件部署

  - 用本包的 `src` 文件夹覆盖原项目的 `src`。
  - 将 `run_publish_cli.py` 和 `mcp_server.py` 放入根目录。

## 🚀 使用方法

### 1. 命令行运行

```bash
python run_publish_cli.py --json_path "/path/to/final_post.json" --images "/path/to/img1.jpg"
```

### 2. MCP 服务配置

**注意**：需设置 `PYTHONPATH` 以便找到 `src` 模块。

```json
"publisher_server": {
  "command": "python",
  "args": ["<YOUR_PROJECT_PATH>/xhs-toolkit/mcp_server.py"],
  "env": {
    "PYTHONPATH": "<YOUR_PROJECT_PATH>/xhs-toolkit"
  }
}
```
