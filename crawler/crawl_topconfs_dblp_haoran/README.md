````markdown
# crawl_topconfs_dblp.py

## 这个脚本是干嘛的？

`crawl_topconfs_dblp.py` 是一个**从 DBLP 自动爬取顶会论文、按方向打标签并存成 CSV** 的小工具。当前默认支持的会议和年份：

- 会议：`CVPR`, `ICCV`, `ECCV`, `ICLR`, `ICML`, `MICCAI`, `NeurIPS`
- 年份范围：`2021–2025`

脚本会调用 DBLP 的 publication API，按每年每个会议的 TOC（`*.bht`）抓取论文列表，解析出题目 / 作者 / DOI / 链接等信息，并且用一套预定义关键词做**多标签分类**，把每篇论文归到一些方向上，比如：

- 训练范式：`pretrain`, `self_supervised`
- 典型任务：`segmentation`, `detection`, `classification`, `generation`, `reconstruction`, `registration`, `tracking`, `pose`, `video`, `three_d`, `multimodal`
- 学习设定 / 泛化：`fewshot`, `semi_supervised`, `domain_adaptation`, `robustness`
- 模型类型：`graph`, `rl`, `transformer`
- 应用领域：`medical`, `autonomous_driving`, `nlp`
- 兜底类：`other`（如果没有匹配到任何方向）

最终为每个会议生成一个 CSV，比如：

- `data_dblp/CVPR_2021_2025_dblp.csv`
- `data_dblp/NeurIPS_2021_2025_dblp.csv`
- …

这些 CSV 就是后续趋势分析、画图、小红书文案生成等下游脚本的基础数据。

---

## 环境要求

- Python 版本：推荐 **Python 3.8+**
- 主要依赖：
  - `requests`
  - 标准库：`time`, `os`, `csv`, `typing` 等

安装依赖示例：

```bash
pip install requests
````

建议在虚拟环境里运行（可选）：

```bash
# 创建虚拟环境
python -m venv .venv

# 激活（Windows PowerShell）
.venv\Scripts\Activate.ps1

# 或 Linux / macOS
# source .venv/bin/activate

pip install requests
```

---

## 文件结构 & 输出结果

运行脚本后，会自动创建一个输出目录（默认：`data_dblp/`），并在其中生成若干 CSV 文件：

```text
data_dblp/
  ├── CVPR_2021_2025_dblp.csv
  ├── ICCV_2021_2025_dblp.csv
  ├── ECCV_2021_2025_dblp.csv
  ├── ICLR_2021_2025_dblp.csv
  ├── ICML_2021_2025_dblp.csv
  ├── MICCAI_2021_2025_dblp.csv
  └── NeurIPS_2021_2025_dblp.csv
```

每个 CSV 的主要列包括（简化说明）：

* 元信息

  * `conference`：会议名（如 `CVPR`）
  * `year_target`：目标年份（脚本里指定的年份，比如 2021）
  * `year_dblp`：DBLP 记录里的年份（有时会略有差异）
  * `title`：论文标题
  * `venue`：出版 venue 信息
  * `authors`：作者列表（用 `; ` 分号分隔）
  * `doi`：DOI
  * `ee_url`：电子版链接 / URL
  * `dblp_key`：DBLP 的唯一 key
  * `categories`：该论文命中的方向标签，用 `;` 拼接（如 `pretrain;multimodal`）

* 各方向的 0/1 标签（多标签）：

  * `is_pretrain`, `is_self_supervised`, `is_segmentation`, …
  * `is_medical`, `is_autonomous_driving`, `is_nlp`
  * `is_other`（如果所有其它标签都是 0，就会置为 1）

---

## 如何运行

假设你已经把脚本放在某个工程目录中，例如：

```text
Practise-Agent-Kits/
  ├── crawl_topconfs_dblp.py
  ├── analyze_ai_confs_with_llm.py
  └── xhs_publisher.py
```

在该目录下打开终端 / PowerShell：

```bash
# 进入项目目录
cd /path/to/Practise-Agent-Kits

# （可选）激活虚拟环境
# .venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate   # Linux / macOS

# 直接运行脚本
python crawl_topconfs_dblp.py
```

运行过程中，命令行会打印类似日志：

* 正在抓取哪个会议、哪一年
* 每个 DBLP 卷（`*.bht`）抓到了多少条记录
* 最终每个会议总共抓到多少篇论文
* 写出 CSV 的路径和行数

脚本内置了对 DBLP API 的限流处理和简单重试机制：如果被 429（Too Many Requests）限制，会自动 sleep 然后继续。

---

## 配置说明

### 1. 修改年份范围

在脚本顶部有一行：

```python
YEARS = list(range(2021, 2026))
```

这是 Python 的左闭右开写法，表示年份为：2021, 2022, 2023, 2024, 2025。

如果你只想拉 2023–2024，可以改成：

```python
YEARS = [2023, 2024]
# 或 YEARS = list(range(2023, 2025))
```

### 2. 修改会议集合

脚本里会定义一个 `CONFERENCES` 字典（如果你那版脚本是 dict 形式），用于配置会议及其对应的 DBLP BHT 路径模式，例如：

```python
CONFERENCES = {
    "CVPR": {
        "type": "single",
        "pattern": "db/conf/cvpr/cvpr{year}.bht",
    },
    "ECCV": {
        "type": "multi",
        "pattern": "db/conf/eccv/eccv{year}-{index}.bht",
        "max_volumes": 30,
    },
    # ...
}
```

* `type = "single"`：说明这一年只有一个卷（一个 `*.bht`）
* `type = "multi"`：说明这一年有多个卷（`-1, -2, ...`）
* `pattern`：BHT key 的格式，会自动用 `year` / `index` 格式化

如果你以后想加别的会议，可以仿照这里再添加一个条目。

### 3. 调整方向关键词

标题分类逻辑在 `CATEGORY_KEYWORDS` 这个大字典里，每个方向对应一组关键词。脚本会把论文标题转为小写，然后做字符串包含判断，只要命中任意一个关键词，就会把它归到该方向，并把对应的 `is_xxx` 置为 1。

示例（伪代码形态）：

```python
CATEGORY_KEYWORDS = {
    "pretrain": [
        "pre-train", "pretrain", "pretraining", "pre-training",
        "pre-trained", "pretrained",
        "foundation model", "foundation models",
        "large language model", "large-language model", " llm ", " llms ",
        # ...
    ],
    "multimodal": [
        "vision-language", "multimodal", "multi-modal",
        # ...
    ],
    # ...
}
```

如果你觉得某个方向漏掉了关键词，或者想新增方向，比如 `audio`、`robotics`，可以在这里增删改；脚本会自动给每篇论文加上对应的 `is_audio` 等字段。

> 注意：如果一篇论文里一个关键词都没命中，脚本会把 `is_other=1` 作为兜底。

---

## 运行中的注意事项

1. **网络 & 代理**

   * 脚本会频繁访问 `https://dblp.org/search/publ/api`，请保证网络能访问 DBLP。
   * 如需代理，可以在运行前配置系统代理（如 `HTTPS_PROXY`），脚本本身不强制写死代理。

2. **限流**

   * DBLP 有一定请求频率限制：

     * 每页抓取之间会 `time.sleep(...)` 做节流。
     * 收到 HTTP 429 时会指数退避重试。
   * 不建议随意把间隔调得太小。

3. **重复运行**

   * 脚本可重复运行，每次会覆盖 `data_dblp/CONF_2021_2025_dblp.csv`。
   * 如果想保留旧版本，可以先手动备份 `data_dblp` 目录。

---

## 和后续脚本的关系（整体项目视角）

典型使用流程是这样一条 pipeline：

1. **本脚本**：`crawl_topconfs_dblp.py`
   → 从 DBLP 抓数据，生成 `data_dblp/*.csv`

2. **分析脚本**：`analyze_ai_confs_with_llm.py`
   → 读取这些 CSV，做统计、画图、调用 LLM 生成小红书文案

3. **发布脚本**：`xhs_publisher.py`
   → 读取指定年份/趋势的图 + 文案，生成适合发小红书的素材或自动发布

