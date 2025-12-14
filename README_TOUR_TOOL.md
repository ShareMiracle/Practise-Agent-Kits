# 旅游攻略图片生成工具

## 概述

这是一个基于 **MCP（Model Context Protocol）协议**的工具：

- 生成旅游攻略长图（竖版海报）
- 发布图文笔记到小红书

## 功能模块

本项目包含以下两个 MCP 服务器模块，每个模块都提供了一组特定的工具（Tool）供调用。

### 1. 🎨 图片生成服务器 (`middleware/middleware_tour_schedule_generation/generate_mcp.py`)

**功能：** 调用 Nano Banana API 生成旅游攻略长图（竖版海报），特别支持四行格式的详细图片描述，适用于小红书等平台。

| 可用工具 | 描述 |
| :--- | :--- |
| `travel_image_prompt_guide` | 生成旅游攻略长图的提示词框架。 |
| `generate_image_nano_banana` | 调用 API 生成图片。 |

**特色：**
*   自动生成一日游攻略长图（竖版海报）。
*   支持早、中、晚三个时段的景点展示。
*   自动保存生成的图片到本地。

### 2. 📱 小红书发布服务器 (`publisher/publisher_tour_schedule_generation/publish_mcp.py`)

**功能：** 自动化发布旅游内容到小红书平台，支持图文笔记和视频笔记的发布。

| 可用工具 | 描述 |
| :--- | :--- |
| `publish_xiaohongshu_images` | 发布图文笔记到小红书。 |
| `validate_xiaohongshu_content` | 审核标题/正文/话题是否超限。 |

**依赖：** 需要已登录的浏览器会话（如通过 Selenium 维护）。

## 快速开始

### 环境要求

*   Python 3.10+
*   Nano Banana API Token（用于图片生成）
*   Chrome + ChromeDriver（用于小红书发布；或使用 Selenium Manager 自动解析）

### 安装依赖

使用 `pip` 安装所需的 Python 库：

```bash
pip install mcp requests selenium
```

### 配置步骤

#### 1. 获取 API Key

*   **Nano Banana API Token：** 访问 [acedata.cloud](https://acedata.cloud/) 注册并获取。

并通过环境变量配置：

```bash
export NANO_BANANA_API_TOKEN="你的token"
```

#### 2. 配置 Cline MCP 设置

将以下 JSON 配置内容保存为 `cline_mcp_settings.json` 文件，并放置在 Cline 的配置目录中。

**注意：** 请根据您的系统环境修改 `command`、`args` 和 `cwd` 中的路径，以及 `env` 中的 API Key。

```json
{
  "mcpServers": {
    "image-generator": {
      "autoApprove": ["generate_image_nano_banana"],
      "disabled": false,
      "timeout": 300,
      "type": "stdio",
      "command": "你的Python解释器路径",
      "args": ["你的项目路径/middleware/middleware_tour_schedule_generation/generate_mcp.py"],
      "cwd": "你的项目路径"
      "env": {
        "NANO_BANANA_API_TOKEN": "你的token"
      }
    },
    "xiaohongshu-publisher": {
      "autoApprove": ["publish_xiaohongshu_images", "validate_xiaohongshu_content"],
      "disabled": false,
      "timeout": 300,
      "type": "stdio",
      "command": "你的Python解释器路径",
      "args": ["你的项目路径/publisher/publisher_tour_schedule_generation/publish_mcp.py"],
      "cwd": "你的项目路径"
    }
  }
}
```

**路径修改说明：**

| 路径类型 | Windows 示例 | macOS/Linux 示例 |
| :--- | :--- | :--- |
| Python 解释器路径 | `E:\APP\Anaconda22\envs\mcp\python.exe` | `/path/to/your/python3` |
| 项目路径 | `E:\PostGraduate\courses\yingxiang\Finaltask\MCPProject` | `/path/to/your/MCPProject` |

## 使用示例

以下是使用各个模块工具的 Python 示例代码：

### 1. 生成旅游攻略图片

```python
# 生成苏州一日游攻略图片
prompt_guide = travel_image_prompt_guide("苏州", "晴天 20度")

# 根据提示词生成图片
result = generate_image_nano_banana(
    prompt=prompt_guide,
    width=1024,
    height=2048
)
```

### 2. 发布到小红书

```python
# 发布图文笔记
publish_xiaohongshu_images(
    file_path="generated_images/苏州旅游攻略.png",
  title="苏州一日游攻略｜超出片路线",
  content="整理了一条超适合拍照的一日游路线，照着走不踩雷。",
  topics=["#苏州旅游", "#旅游攻略", "#周末去哪儿", "#拍照打卡"]
)
```

## 配置说明

### Cline 配置文件位置

`cline_mcp_settings.json` 文件应放置在以下目录（以 VS Code 为例）：

| 操作系统 | 路径 |
| :--- | :--- |
| Windows | `%APPDATA%\Code\User\globalStorage\codeium.codeium\config\cline_mcp_settings.json` |
| macOS | `~/Library/Application Support/Code/User/globalStorage/codeium.codeium/config/cline_mcp_settings.json` |
| Linux | `~/.config/Code/User/globalStorage/codeium.codeium/config/cline_mcp_settings.json` |

### 环境变量配置

在运行 MCP 服务器之前，建议设置以下环境变量：

```bash
# 设置 Nano Banana API Token
export NANO_BANANA_API_TOKEN="你的token"

# 设置 Python 路径（如果需要）
export PYTHONPATH="你的项目路径:$PYTHONPATH"
```

## 注意事项

*   **API 限制：** Nano Banana API 可能有调用限制，请注意遵守服务商的使用条款。
*   **小红书发布：**
    *   需要已登录的浏览器会话。
    *   需要安装 Chrome 浏览器和对应版本的 ChromeDriver。
    *   首次使用需要手动登录小红书账号。
*   **数据安全：**
    *   API Key 等敏感信息**切勿**提交到版本控制系统（如 Git）。
    *   建议使用环境变量或配置文件来管理敏感信息。
*   **路径问题：**
    *   Windows 系统路径使用反斜杠 `\` 或双反斜杠 `\\`。
    *   macOS/Linux 系统路径使用正斜杠 `/`。

## 故障排除

1.  **MCP 服务器无法启动：**
    *   检查 `cline_mcp_settings.json` 中配置的 Python 解释器路径是否正确。
    *   确保已通过 `pip install` 安装了所有依赖包。
    *   检查配置文件中的项目路径 (`cwd` 和 `args`) 是否存在。
2.  **API 调用失败：**
    *   检查 API Key 是否有效，并确保已正确配置在环境变量或配置文件中。
    *   检查网络连接是否正常。
    *   查看 API 服务商的状态页面，确认服务是否可用。
3.  **小红书发布失败：**
    *   检查是否已成功登录小红书账号。
    *   检查 ChromeDriver 版本是否与您安装的 Chrome 浏览器版本匹配。
    *   检查待发布的文件路径是否正确。

## 项目结构

```
MCPProject/
├── data/                    # 可选：你自己的素材/数据目录
├── generated_images/        # 生成的图片
├── cline_mcp_settings.json  # Cline 配置文件
├── publisher/               # 发布相关 MCP
│   └── publisher_tour_schedule_generation/
│       └── publish_mcp.py        # 小红书发布服务器
├── middleware/              # 通用中间层/工具代码
│   └── middleware_tour_schedule_generation/
│       ├── upload_utils.py       # 小红书上传/发布相关工具
│       ├── web_utils.py          # Selenium/浏览器工具
│       └── generate_mcp.py       # 图片生成服务器
└── README.md                # 项目说明文档
```

## 许可证

本项目仅供学习和研究使用，请遵守相关 API 服务商的使用条款。

## 贡献

欢迎通过提交 Issue 和 Pull Request 来改进和完善本项目。

## 支持

如果您在使用过程中遇到问题，请：
1.  仔细查阅本 README 文档。
2.  检查配置文件中的路径和 API Key 是否正确。
3.  查看各个 MCP 服务器的日志输出以获取详细错误信息。
