````markdown
# analyze_ai_confs_with_llm.py

基于顶会论文统计结果，一键生成「AI 顶会趋势可视化 + 小红书风格解读文案」的脚本。:contentReference[oaicite:0]{index=0}  

它会读取 `data_dblp/` 下多个会议的 CSV，做聚合分析，输出一系列图表，并调用 LLM 自动写好年度回顾 & 2021–2025 趋势+2026 预测的中文文案。

---

## 功能概览

运行一次脚本，会完成：

1. **数据聚合**
   - 读取 `CSV_DIR`（默认 `data_dblp/`）下的：
     - `CVPR_2021_2025_dblp.csv`
     - `ECCV_2021_2025_dblp.csv`
     - `ICCV_2021_2025_dblp.csv`
     - `ICLR_2021_2025_dblp.csv`
     - `ICML_2021_2025_dblp.csv`
     - `MICCAI_2021_2025_dblp.csv`
     - `NeurIPS_2021_2025_dblp.csv`
   - 假设这些 CSV 来自前置脚本 `crawl_topconfs_dblp.py`，列中包含：
     - `year_target`：目标年份（2021–2025）
     - `conference`：会议名
     - `title`：论文标题
     - 一系列 `is_xxx` 标签列（如 `is_pretrain`, `is_segmentation`, `is_generation` …）

2. **统计与分析**
   - 对每一个年份（2021–2025）统计：
     - 总论文数 `total_papers`
     - 各类别的论文数和占比 `category_stats`
     - Top-3 热门方向 `top_categories`
   - 构建 2021–2025 整体趋势：
     - 每年的总论文数
     - 每个方向随时间的论文数量变化

3. **可视化输出（存到 `figs/`）**
   - 年度 top12 方向柱状图：`figs/year_bars/year_YYYY_top_categories.png`
   - 关键方向趋势折线图 & 堆叠图：`figs/trends/*.png`
   - 方向占比演化堆叠图：`figs/stacked_share/category_share_2021_2025.png`
   - 卷王榜：
     - 总量 Top-N：`figs/category_leaderboards/top_total_categories.png`
     - 增长倍率 Top-N：`figs/category_leaderboards/top_growth_categories.png`
   - 会议 × 方向：
     - 热力图：`figs/conf_category/conf_category_heatmap.png`
     - 气泡图：`figs/conf_category/conf_category_bubble.png`
   - 会议人设雷达图（每个会议一张）：`figs/conf_radar/radar_{CONF}.png`
   - 封面插画文案 & 可选自动封面图：
     - 文本 prompt：`figs/cover_image_prompt.txt`
     - 自动生成插画（如果配置了图像 API）：`figs/cover_image.png`

4. **小红书风格文案生成（存到 `llm_reports/`）**
   - 每一年一份年度回顾文案：
     - `llm_reports/year_2021_summary.md`
     - …
     - `llm_reports/year_2025_summary.md`
   - 一篇 2021–2025 总体趋势 + 2026 预测：
     - `llm_reports/trend_2021_2025_and_forecast.md`

---

## 依赖环境

- Python >= 3.9
- 主要依赖：
  - `pandas`
  - `numpy`
  - `matplotlib`
  - `requests`

可以用 `pip` 安装，例如：

```bash
pip install pandas numpy matplotlib requests
````

---

## 配置说明

脚本通过环境变量控制 LLM 和图像生成后端：

### 1. 数据目录

```python
CSV_DIR = "data_dblp"
CONFERENCES = ["CVPR", "ECCV", "ICCV", "ICLR", "ICML", "MICCAI", "NeurIPS"]
```

* 请确保在项目根目录下存在 `data_dblp/` 文件夹，并包含上述会议对应的 `*_2021_2025_dblp.csv`。
* **建议**：先运行 `crawl_topconfs_dblp.py` 自动爬取并生成这些 CSV，再运行本分析脚本。

---

### 2. LLM 配置（用于生成文案）

脚本默认使用 OpenRouter 兼容的 Chat API：

```python
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://openrouter.ai/api/v1")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "...")
LLM_MODEL    = os.getenv("LLM_MODEL", "tngtech/deepseek-r1t2-chimera:free")
```

**推荐做法：**

在终端中设置环境变量（Linux / macOS）：

```bash
export LLM_API_BASE="https://openrouter.ai/api/v1"
export LLM_API_KEY="sk-or-xxxxxx"          # 你的 OpenRouter API Key
export LLM_MODEL="tngtech/deepseek-r1t2-chimera:free"
```

Windows PowerShell 示例：

```powershell
$env:LLM_API_BASE="https://openrouter.ai/api/v1"
$env:LLM_API_KEY="sk-or-xxxxxx"
$env:LLM_MODEL="tngtech/deepseek-r1t2-chimera:free"
```

> 注意：仓库里的默认 key 应该删掉 / 改成环境变量方式，避免泄露真实密钥。

---

### 3. 图像生成配置

脚本支持两种封面插画生成方式：

1. **Hugging Face Inference API（推荐）**

   ```python
   IMAGE_BACKEND = os.getenv("IMAGE_BACKEND", "hf")
   HF_API_TOKEN  = os.getenv("HF_API_TOKEN", "")
   HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
   ```

   设置环境变量：

   ```bash
   export IMAGE_BACKEND="hf"
   export HF_API_TOKEN="hf_xxx"   # 需要有 Inference 权限的 token
   # 可选：更换模型
   export HF_IMAGE_MODEL="stabilityai/stable-diffusion-xl-base-1.0"
   ```

2. **OpenRouter 图像模型**

   ```python
   IMAGE_BACKEND = "openrouter"
   ```

   环境变量：

   ```bash
   export IMAGE_BACKEND="openrouter"
   export LLM_API_KEY="sk-or-xxxxxx"
   export LLM_IMAGE_MODEL="your-image-model-id"
   ```

如果不配置图像后端，脚本仍然会生成 `figs/cover_image_prompt.txt`，只是不会自动生成图片。

---

## 如何运行

### 1. 准备 CSV 数据

1. 确保已经运行过爬虫脚本（例如 `crawl_topconfs_dblp.py`），在项目根目录下生成：

   * `data_dblp/CVPR_2021_2025_dblp.csv`
   * `data_dblp/ICLR_2021_2025_dblp.csv`
   * ……

2. CSV 至少应包含以下列：

   * `year_target`
   * `conference`
   * `title`
   * 与 `CATEGORY_COLS` 对应的若干 `is_xxx` 列（例如 `is_pretrain`, `is_generation`, `is_multimodal` 等）

### 2. 设置环境变量（LLM / 图像生成）

参考上面的配置说明，根据你实际使用的服务设置 `LLM_API_KEY`、`HF_API_TOKEN` 等。

### 3. 直接运行脚本

在项目根目录下执行：

```bash
python analyze_ai_confs_with_llm.py
```

运行过程大致会：

* 打印每年统计情况，例如：

  * `[INFO] 2021 年：总论文 xxx 篇，top1 = pretrain (yyy 篇)`
* 打印图像生成和保存路径：

  * `[OK] Saved figure: figs/year_bars/year_2021_top_categories.png`
  * `[OK] Saved trend line figure: figs/trends/trend_focus_multi_lines.png`
  * `...`
* 调用 LLM 生成各年份的小红书文案：

  * `[LLM] 正在生成 2021 年的总结……`
  * `[OK] 保存 2021 年总结到 llm_reports/year_2021_summary.md`
* 最后生成整体趋势 + 2026 预测文案：

  * `[LLM] 正在生成 2021–2025 整体趋势分析和 2026 预测……`
  * `[OK] 保存整体趋势报告到 llm_reports/trend_2021_2025_and_forecast.md`

---

## 输出目录结构示例

运行完成后，大致会看到：

```text
project_root/
├── data_dblp/
│   ├── CVPR_2021_2025_dblp.csv
│   ├── ICCV_2021_2025_dblp.csv
│   └── ...
├── figs/
│   ├── year_bars/
│   │   ├── year_2021_top_categories.png
│   │   └── ...
│   ├── trends/
│   │   ├── trend_focus_multi_lines.png
│   │   └── trend_focus_stack_area.png
│   ├── stacked_share/
│   │   └── category_share_2021_2025.png
│   ├── category_leaderboards/
│   │   ├── top_total_categories.png
│   │   └── top_growth_categories.png
│   ├── conf_category/
│   │   ├── conf_category_heatmap.png
│   │   └── conf_category_bubble.png
│   ├── conf_radar/
│   │   ├── radar_CVPR.png
│   │   ├── radar_ICLR.png
│   │   └── ...
│   ├── cover_image_prompt.txt
│   └── cover_image.png        # 如果配置了图像生成
├── llm_reports/
│   ├── year_2021_summary.md
│   ├── year_2022_summary.md
│   ├── ...
│   └── trend_2021_2025_and_forecast.md
└── analyze_ai_confs_with_llm.py
```

---

## 常见问题 & 小贴士

* **报错：没有读到任何 CSV**

  * 检查 `CSV_DIR` 路径是否正确，是否真的有 `*_2021_2025_dblp.csv` 文件。
* **报错：LLM_API_KEY 未设置 / 429 限流**

  * 确认已正确配置 OpenRouter API Key；
  * 多次 429 时脚本会自动退避重试，如果一直失败可以稍后再跑。
* **图像没有生成**

  * 确认是否设置了 `IMAGE_BACKEND` 和对应的 `HF_API_TOKEN` 或 `LLM_IMAGE_MODEL`；
  * 若不需要自动插画，仅使用 `cover_image_prompt.txt` 也完全没问题，可以手动丢到任意图像模型里生成。

---

## 典型使用场景

* 课程 / 小组展示：
  一键生成顶会论文趋势图 + 配套中文解读文案，直接放进 PPT 或小红书展示。
* 自己选题 / 看方向：
  快速看出 2021–2025 哪些方向「整体在涨」、哪些是「黑马」。
* 内容创作：
  直接用 `llm_reports` 里的 md 文案，稍微修改就可以发小红书、公众号等。


