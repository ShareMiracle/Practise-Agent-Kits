# Conference Schedule Crawler

本模块用于 **自动抓取学术会议官网的日程页面（Schedule / Calendar）**，
并将 **完整原始 HTML** 及 **可读清洗文本** 保存到本地，作为后续
个性化日程生成、可视化、信息抽取的基础数据。

---

## ✨ 功能简介

- 🌐 自动访问会议官网日程页面
- 💾 保存 **原始 HTML**（用于后续精确解析，强烈推荐）
- 📝 同时生成一份 **清洗后的纯文本版本**（便于人工查看 / debug）
- 🧩 支持通过命令行参数指定会议名称和年份
- 🏗️ 结构清晰，方便扩展到更多会议

---

## 📂 文件结构

```text
Conference_schedule_crawler/
├── fetch_schedule.py
├── schedule_data/
│   ├── CVPR_2025_raw.html
│   └── CVPR_2025_clean.txt
│   └── ...
├── README.md
└── requirements.txt
```

## 🔧 支持的会议（当前）

在代码中通过 CONFERENCE_SCHEDULE_URLS 映射配置：

- CVPR 2025

- ICCV 2025

- ICLR 2025

- ICML 2025

- NeurIPS 2025

- MICCAI 2025

如需新增会议，只需在字典中添加：

```python
("CONF_NAME", YEAR): "https://conference-website/calendar"
```

## 🚀 使用方法
### 1️⃣ 安装依赖
``` bash
pip install -r requirements.txt
```

### 2️⃣ 命令行运行（推荐）
``` bash
python fetch_schedule.py \
  --conference CVPR \
  --year 2025
```

成功后你会看到类似输出：
``` text
🌐 抓取 CVPR 2025 官网日程...
✅ 原始 HTML 已保存：agent_part2/schedule_data/CVPR_2025_raw.html
📝 清洗文本已保存：agent_part2/schedule_data/CVPR_2025_clean.txt
```
### 3️⃣ 作为 Python 函数调用
``` python
from fetch_schedule import fetch_and_save_schedule

html_path, txt_path = fetch_and_save_schedule("CVPR", 2025)
```

返回值：

- html_path：原始 HTML 路径

- txt_path：清洗文本路径

## 📄 输出文件说明

### 1️⃣ 原始 HTML（*_raw.html）【最重要】

- 完整保存官网返回内容

- 用于后续：

- - 精确解析时间、session、room

- - 处理并行 session

- - AI 日程理解与推荐

*⚠️ 后续解析请始终以 HTML 为准*

### 2️⃣ 清洗文本（*_clean.txt）【辅助】

- 去除 HTML 标签，仅保留可读文本

- 主要用途：

- - 快速人工浏览

- - Debug

- - Prompt 验证

不建议作为最终解析数据源

## 🧠 设计理念说明

### 为什么不直接解析日程？

- **不同会议官网结构差异极大**  
  每个会议的网页布局、HTML 结构和样式都可能完全不同。

- **很多日程由 JavaScript 动态渲染**  
  直接使用静态 HTML 解析无法获取通过 JS 动态加载的内容。

- **直接解析容易在官网更新后失效**  
  一旦会议官网改版，原有的解析规则很可能立即失效，维护成本高。

## 👉 本模块设计原则
**只做 “可靠抓取 + 原始数据保留”**  
将解析逻辑剥离，交由后续的 **LLM / 专用解析器（Parser）** 处理。  
这样即使网页结构变化，也只需调整后续解析策略，而不影响数据抓取的稳定性。

---

## ⚠️ 常见问题

### ❌ 未配置会议 URL

**如果运行时报错：**
**说明该会议 + 年份尚未加入 `CONFERENCE_SCHEDULE_URLS`。**  
请检查配置并添加对应的会议年份与日程页 URL。

### ❌ 请求失败 / 超时

- **请确认网络环境正常**  
  确保可以正常访问目标会议官网。

- **部分官网可能需要更新 URL**  
  某些会议每年日程页路径可能发生变化，请确认 URL 是否仍然有效。

- **可适当增大 timeout（默认 20 秒）**  
  如果网络较慢或页面加载时间长，可尝试增加超时时间。

---

## 🧑‍💻 作者与许可

* 作者：[Siyan Zhuo](https://github.com/Zhuosy)
* License: **Unlicense**（公共领域，无任何使用限制）

> 你可以自由地使用、修改、分发本项目的全部或部分内容，无需署名或许可。


