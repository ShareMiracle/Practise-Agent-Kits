# 一键全流程脚本说明（run_full_pipeline.py & run_all.sh）

这个 README 说明的是**一键跑完整小红书素材生产流程**的两个入口脚本：

* `run_full_pipeline.py`：Python 版一键脚本
* `run_all.sh`：简单 Bash 包装脚本，方便在 Linux / Mac 上一条命令执行

整个流程会依次完成：

1. 从 DBLP 抓取指定顶会 2021–2025 年论文列表，并保存为 CSV
2. 对 CSV 做统计分析 + 画图 + 调 LLM 生成小红书风格文案
3. 根据图表和文案，打包所有小红书「素材包」到一个统一目录，方便你挑选发布

---

## 一、整体流程概览

`run_full_pipeline.py` 内部按顺序调用三个模块：

1. `crawl_topconfs_dblp.main()`

   * 从 DBLP 抓取顶会（如 CVPR、ICCV、ECCV、ICLR、ICML、MICCAI、NeurIPS）论文
   * 按年份整理并保存到 `data_dblp/*.csv`

2. `analyze_ai_confs_with_llm.main()`

   * 读取 `data_dblp/*.csv`
   * 统计各方向论文数量 / 占比，画出多张趋势图、热力图等
   * 调用 LLM 生成按年份的年度回顾文案（小红书风格），以及 2021–2025 趋势 + 2026 展望文案
   * 文案保存到 `llm_reports/`，图片保存到 `figs/` 下的各子目录

3. `xhs_publisher.export_all_notes()`

   * 读取 `llm_reports/` 文案和 `figs/` 中的图像
   * 为每一年 + 整体趋势组装一个小红书「素材包」
   * 每个素材包通常包含：推荐封面图、正文图若干、对应的中文文案
   * 最终统一打包到 `xhs_exports/`，用于你手动上传小红书

脚本会为每一步打印类似下面这种有边框的日志，方便你录屏讲解和 debug：

```text
========================================================================
[STEP 1] 抓取 DBLP 并生成 data_dblp/*.csv
========================================================================
...
[STEP 1 DONE] 抓取 DBLP 并生成 data_dblp/*.csv 结束，耗时 XX.X 秒
```

所有步骤完成后，会有总耗时统计，并提示你去 `xhs_exports/` 里挑素材：

```text
[ALL DONE] 全流程执行完毕 ✅
总耗时 XXX.X 秒
现在可以去 xhs_exports/ 里挑选你要发的小红书素材包了～
```

---

## 二、环境准备

### 1. Python 环境

建议使用：

* Python 3.9+（3.10/3.11 也可以）
* 推荐创建一个虚拟环境（conda / venv 均可）

基础依赖大致包括（根据你自己的脚本为准）：

* `requests`
* `pandas`
* `matplotlib`
* 以及 `crawl_topconfs_dblp.py`、`analyze_ai_confs_with_llm.py`、`xhs_publisher.py` 里用到的其他库

可以在项目根目录手动安装，例如：

```bash
pip install -r requirements.txt
```

（如果你还没写 `requirements.txt`，也可以直接按需 `pip install`。）

### 2. LLM / 图片相关环境变量

部分模块会调用 LLM 和图片生成 API，请在运行前配置好环境变量（在终端里 `export` / `set` 即可）：

* `LLM_API_BASE`（可选，默认为 `https://openrouter.ai/api/v1`）
* `LLM_API_KEY`（必需，用于调用 OpenRouter 兼容接口）
* `LLM_MODEL`（可选，默认你在脚本中设定的模型）

如使用 Hugging Face 生成封面图，还需要：

* `IMAGE_BACKEND=hf`
* `HF_API_TOKEN`（需具备 Inference 权限）
* `HF_IMAGE_MODEL`（可选，默认 `stabilityai/stable-diffusion-xl-base-1.0`）

如果你只想跑文本和统计图，不需要自动画封面图，也可以暂时不配置 `HF_API_TOKEN`，脚本会只写出 prompt 文本。

---

## 三、如何一键运行（Python 方式）

在项目根目录（也就是包含 `run_full_pipeline.py` 和那三个模块的目录）下执行：

```bash
python run_full_pipeline.py
```

在 Windows 上通常是：

```bash
py run_full_pipeline.py
```

运行后会自动：

1. 抓取 DBLP -> `data_dblp/*.csv`
2. 分析 + 画图 + 生成文案 -> `figs/` & `llm_reports/`
3. 打包所有小红书素材 -> `xhs_exports/`

你只需要等它跑完（录屏的话中间可以后期快进），最后直接打开 `xhs_exports/` 挑选要发的小红书图文即可。

---

## 四、如何一键运行（Bash 脚本方式）

在 Linux / Mac（或 WSL）上，你可以直接用 `run_all.sh` 来跑：

```bash
bash run_all.sh
```

`run_all.sh` 做的事情很简单：

1. `cd` 到脚本所在目录，保证相对路径正确
2. 调用你本机的 `python` 去执行 `run_full_pipeline.py`

如果你的 Python 命令是 `python3`，可以打开 `run_all.sh` 把里面的命令改成：

```bash
python3 run_full_pipeline.py
```

---

## 五、目录 & 产出说明（录屏讲解用）

完整跑完一遍流程后，你可以在视频里展示大致这些目录和内容（根据你实际项目为准）：

* `data_dblp/`

  * 若干 `XXX_2021_2025_dblp.csv` 文件
  * 每个文件对应一个顶会，里面是 2021–2025 年的论文列表 + 标注字段

* `figs/`

  * `year_bars/`：每年 Top 方向柱状图
  * `trends/`：折线图 / 堆叠面积图等
  * `stacked_share/`：方向占比随时间变化的堆叠图
  * `category_leaderboards/`：总量 / 增长黑马排行榜
  * `conf_category/`：会议 × 方向热力图 & 气泡图
  * `conf_radar/`：每个会议的人设雷达图
  * `cover_image_prompt.txt` & `cover_image.png`：封面图 prompt 和实际生成的封面图（如果已启用图片生成）

* `llm_reports/`

  * `year_2021_summary.md` ~ `year_2025_summary.md`：每一年的小红书风格年度回顾文案
  * `trend_2021_2025_and_forecast.md`：整体趋势 + 2026 预测文案

* `xhs_exports/`

  * 按你在 `xhs_publisher.py` 里设计的结构，通常是每个素材包一个子目录：

    * 包含：推荐封面图、正文图、对应年份的文案 `.txt` 或 `.md`
  * 你可以在录屏里随便点开一个年份的素材包，展示**图片 + 文案**如何一一对应，方便后续手动上传小红书。

---

## 六、常见问题（简要）

1. **脚本中某一步报错怎么办？**
   `run_full_pipeline.py` 对每一步都有 try/except 包裹，遇到异常会打印详细 traceback，并说明是哪个 STEP 出错。你可以根据报错信息单独运行对应的 Python 脚本调试（例如只跑 `crawl_topconfs_dblp.py`）。

2. **想只更新文案 / 图，不重新爬 DBLP？**
   可以暂时手动直接跑第二步或第三步对应的脚本，例如：

   ```bash
   python analyze_ai_confs_with_llm.py
   python xhs_publisher.py
   ```

   但一键脚本 `run_full_pipeline.py` 默认是 **三步全跑**，保证数据链路一致。


