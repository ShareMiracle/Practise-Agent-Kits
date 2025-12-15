import os
import json
from typing import Dict, List

import pandas as pd
import requests
import matplotlib.pyplot as plt

import numpy as np
import matplotlib
from matplotlib import font_manager
import time
from math import pi
import base64
from matplotlib.colors import LinearSegmentedColormap

# ============ 基本配置 ============

# 你的 CSV 所在目录（根据实际修改）
CSV_DIR = "data_dblp"

# 会议信息（假设文件名格式为 {conf}_2021_2025_dblp.csv）
CONFERENCES = ["CVPR", "ECCV", "ICCV", "ICLR", "ICML", "MICCAI", "NeurIPS"]

# 年份范围
YEARS = list(range(2021, 2026))

# 分类列名（和你 CSV 里的一致）
CATEGORY_COLS = [
    "is_pretrain",
    "is_self_supervised",
    "is_segmentation",
    "is_detection",
    "is_classification",
    "is_generation",
    "is_reconstruction",
    "is_registration",
    "is_tracking",
    "is_pose",
    "is_video",
    "is_three_d",
    "is_multimodal",
    "is_fewshot",
    "is_semi_supervised",
    "is_domain_adaptation",
    "is_robustness",
    "is_graph",
    "is_rl",
    "is_transformer",
    "is_medical",
    "is_autonomous_driving",
    "is_nlp",
    "is_other",
]

CATEGORY_LABELS_EN: Dict[str, str] = {
    "pretrain": "Pretraining / Foundation",
    "self_supervised": "Self-supervised",
    "segmentation": "Segmentation",
    "detection": "Detection",
    "classification": "Classification / Recognition",
    "generation": "Generation / Diffusion / GAN",
    "reconstruction": "Reconstruction / SR",
    "registration": "Registration",
    "tracking": "Tracking / Trajectory",
    "pose": "Pose Estimation / Keypoints",
    "video": "Video / Temporal",
    "three_d": "3D / NeRF / Point Cloud",
    "multimodal": "Multimodal / V+L",
    "fewshot": "Few-shot / Zero-shot",
    "semi_supervised": "Semi / Weakly Supervised",
    "domain_adaptation": "Domain Adaptation / Transfer",
    "robustness": "Robustness / OOD / Privacy",
    "graph": "Graph / GNN",
    "rl": "Reinforcement Learning",
    "transformer": "Transformer / ViT",
    "medical": "Medical Imaging",
    "autonomous_driving": "Autonomous Driving / BEV",
    "nlp": "NLP / Language",
    "other": "Other / Long-tail",
}

FOCUS_CATS_FOR_CONF = [
    "pretrain",
    "segmentation",
    "detection",
    "generation",
    "multimodal",
    "three_d",
    "medical",
    "robustness",
]

RADAR_CATS = [
    "pretrain",
    "segmentation",
    "generation",
    "multimodal",
    "medical",
    "robustness",
]



# ============ LLM API 配置（通用 OpenAI-兼容） ============

LLM_API_BASE = os.getenv("LLM_API_BASE", "https://openrouter.ai/api/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "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")
LLM_MODEL = os.getenv("LLM_MODEL", "tngtech/deepseek-r1t2-chimera:free")

# ============ 图像生成 API 配置（Hugging Face） ============

IMAGE_BACKEND = os.getenv("IMAGE_BACKEND", "hf")  # 'hf' 或 'openrouter'

HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")

# ============ 数据加载与统计 ============

def load_all_papers() -> pd.DataFrame:
    """读取所有会议的 CSV，合并成一个大 DataFrame。"""
    dfs = []
    for conf in CONFERENCES:
        path = os.path.join(CSV_DIR, f"{conf}_2021_2025_dblp.csv")
        if not os.path.exists(path):
            print(f"[WARN] CSV 不存在，跳过: {path}")
            continue
        print(f"[INFO] 读取 {path}")
        df = pd.read_csv(path)
        dfs.append(df)
    if not dfs:
        raise RuntimeError("没有读到任何 CSV，请检查 CSV_DIR 和文件名。")
    df_all = pd.concat(dfs, ignore_index=True)
    return df_all


def build_yearly_stats(df: pd.DataFrame) -> Dict[int, dict]:
    """
    对每一年做聚合统计：
    - total_papers: 总论文数
    - category_stats: 各类别的 count / ratio / example_titles
    - top_categories: 按数量排序的前三个方向
    """
    stats: Dict[int, dict] = {}

    for year in YEARS:
        df_y = df[df["year_target"] == year]
        if df_y.empty:
            print(f"[WARN] {year} 年没有任何论文，跳过。")
            continue

        total = int(len(df_y))
        cat_stats: Dict[str, dict] = {}

        for col in CATEGORY_COLS:
            if col not in df_y.columns:
                continue
            cat_key = col.replace("is_", "")  # 例如 is_pretrain -> pretrain
            count = int(df_y[col].sum())
            ratio = float(count) / total if total > 0 else 0.0

            if count > 0:
                titles = (
                    df_y[df_y[col] == 1]["title"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
                example_titles = titles[:8]  # 每类最多 8 篇代表例
            else:
                example_titles = []

            cat_stats[cat_key] = {
                "count": count,
                "ratio": ratio,
                "example_titles": example_titles,
            }

        sorted_cats = sorted(
            cat_stats.items(), key=lambda kv: kv[1]["count"], reverse=True
        )
        top3 = [
            {
                "category": cat,
                "count": data["count"],
                "ratio": data["ratio"],
            }
            for cat, data in sorted_cats[:3]
            if data["count"] > 0
        ]

        stats[year] = {
            "year": year,
            "total_papers": total,
            "category_stats": cat_stats,
            "top_categories": top3,
        }

        if top3:
            print(
                f"[INFO] {year} 年：总论文 {total} 篇，"
                f"top1 = {top3[0]['category']} ({top3[0]['count']} 篇)"
            )
        else:
            print(f"[INFO] {year} 年：总论文 {total} 篇")

    return stats


def build_trend_data(year_stats: Dict[int, dict]) -> dict:
    """
    构建 2021–2025 的时间序列数据，给大模型做整体趋势分析：
    {
      "years": [2021, 2022, ...],
      "total_papers": {2021: xxx, ...},
      "by_category": {
          "pretrain": [2021_count, 2022_count, ...],
          ...
      }
    }
    """
    years_sorted = sorted(year_stats.keys())
    trend = {
        "years": years_sorted,
        "total_papers": {y: year_stats[y]["total_papers"] for y in years_sorted},
        "by_category": {},
    }

    for col in CATEGORY_COLS:
        cat_key = col.replace("is_", "")
        yearly_counts: List[int] = []
        for y in years_sorted:
            cat_info = year_stats[y]["category_stats"].get(cat_key, {})
            yearly_counts.append(int(cat_info.get("count", 0)))
        trend["by_category"][cat_key] = yearly_counts

    return trend


# ============ Prompt 构造 ============

def make_year_prompt(year: int, year_payload: dict) -> str:
    """
    为某一年的统计数据生成“小红书风格”文案的提示词。
    视角：站在 2025 年的 Papergent，回头复盘这一年。
    """
    year_data_json = json.dumps(year_payload, ensure_ascii=False, indent=2)

    prompt = f"""
你是一名在小红书分享 AI / CV 方向内容的博主，固定人设是：

> 大家好，我是来自中科大苏研院 Miracle Lab 的 Papergent，一只专门帮大家「看论文、避坑选题」的智能小纸人 📄🤖

现在是 **2025 年**，你手上有 2021–2025 年多个 AI 顶会（CVPR, ICCV, ECCV, ICLR, ICML, MICCAI, NeurIPS）的论文统计数据，
已经按主题（pretrain, segmentation, generation, multimodal, medical 等）聚合好了。

下面是 **{year} 年** 的统计 JSON（只给你看，不要原封不动贴出来）：

{year_data_json}

字段说明：
- total_papers: 这一年所有论文总数
- category_stats: 键是类别名（如 "pretrain"），包含 count、ratio、example_titles 等
- top_categories: 按论文数量排序的前三大方向

⚠️ 特别规则：
- 如果 top_categories 里的第一名类别是 "other"，说明这是一个“杂项桶”，请不要把它当成主角分析；
  优先讲之后那些更具体的方向（pretrain, segmentation, generation, multimodal, medical 等）。
- “other” 可以在文案中顺带一提，比如“还有一大堆长尾小方向丢在 other 里”，但不要放在 C 位。

现在请你根据这些数据，写出 **2 条适合发在小红书上的短文案**，要求：

### 整体风格
- 语言：**中文为主**，少量夹带英文术语
- 语气：轻松、有趣、像 Papergent 在跟粉丝聊天，不要论文口吻
- 视角：**明确是 2025 年在回头聊 {year} 这一年的情况**，可以偶尔对比后面几年（比如“后来 2023–2025 证明了这一波趋势”）。
- 长度：每条控制在 **200–400 字** 左右
- 结构：不要用「1. 2. 3.」这种学术大纲，不要用 Markdown 标题 (#)；
  允许适当换行分段，用简单的列表符号（比如「·」或「-」）。

### 每条文案都必须包含的内容

1. **开头人设 + 吸睛标题（2025 视角）**  
   - 第一行用一句标题式的话，比如：  
     - “回到 {year}：这年顶会 AI 到底在卷啥？🔥（来自 2025 的回看）”  
     - “站在 2025 回头看 {year}，原来这一年早就埋好了后面几年的伏笔 📈”  
   - 下一行用一句话口播式自我介绍 + 时间视角：  
     “大家好，我是中科大苏研院 Miracle Lab 的 Papergent，现在在 2025 年，带你回头看看 {year} 那年 AI 顶会都在忙些什么～”

2. **数据来源说明（一定要提 DBLP）**  
   用 1–2 句交代清楚：  
   - 本文所有统计都基于 **DBLP 的论文收录数据**，  
   - 可能不是 100% 完整（有少数论文没收录），  
   - 但对 CVPR/ICLR/NeurIPS 这些主流顶会来说，**已经覆盖绝大多数论文，用来看大盘趋势是足够的**。  
   语气可以稍微幽默一点，比如“就当是 AI 顶会圈的气象台观测数据”。

3. **{year} 年的热点方向（从 2025 回头看）**  
   - 重点讲 2–3 个论文量最多、且不是 "other" 的方向：  
     - 粗略提一下数量级和占比（用“差不多占到总量的 1/5 左右”、“在当年已经是妥妥的主流”等定性描述），  
     - 用很通俗的话概括这些方向在干嘛（根据类别名和 example_titles 合理概括）。  
   - 可以顺带带一点“后视镜”视角：  
     - 比如“从 2025 回头看，这一年在 pretraining 上铺的路，后来直接喂饱了后面几代大模型”；  
     - 或者“当时大家没觉得有多火的方向，后来在 2023–2024 变成黑马”。

4. **少量论文例子（信息量，但不啰嗦）**  
   - 可以从 example_titles 里挑 1–3 个标题：  
     用「《标题》+ 一句吐槽/解读」的形式给出，比如：  
     “《XXXX》这种就是在做多模态检索，主打一个‘让模型顺便读懂图+文’，到 2025 看仍然是很典型的一类工作。”  
   - 不要列很长的 paper list，保持轻量级。

5. **小小选题感受 + 互动问题 + 标签（2025 视角）**  
   - 用 1 段话，从 2025 的视角给正在选题/回顾履历的人一点感觉，比如：  
     “如果你在 {year} 那年选了 pretraining / multimodal，现在大概率已经躺在浪尖上；  
      如果当时选了某些长尾小方向，现在也有可能变成‘冷门宝藏股’。”  
   - 最后抛一个问题让大家评论区互动，例如：  
     “如果能穿越回 {year} 给当年的自己一句选题建议，你会说啥？”  
   - 加上 3–6 个 hashtag（用 # 符号），例如：  
     #AI研究 #顶会复盘 #CVPR #NeurIPS #科研选题 #Papergent

### Emoji 使用
- 每条文案使用 3–8 个 emoji：📈📉📊🤖🧠🔥✨🧪🚗🩻 等都可以
- 不要每句话都塞 emoji，保持自然点缀

### 输出格式
- 一次性输出 2 条文案
- 两条文案之间用一行 `---` 分隔
- 不要再输出 JSON，不要解释你是如何分析的，只给我可以直接复制到小红书里的中文文本

请根据以上要求，结合 {year} 年的数据，**以 2025 年的视角写出这两条年度回顾文案**。
"""
    return prompt




def make_trend_prompt(trend_payload: dict) -> str:
    """
    生成一篇“从 2025 视角看 2021–2025 AI 顶会趋势 + 对 2026 预测”的小红书风格文案。
    """
    trend_json = json.dumps(trend_payload, ensure_ascii=False, indent=2)

    prompt = f"""
你是一名在小红书做 AI 科普&趋势分析的博主，固定人设是：

> 大家好，我是来自中科大苏研院 Miracle Lab 的 Papergent，一只专门帮你看顶会、盘趋势的智能小纸人 📄🤖

**现在是 2025 年**，你手上有 2021–2025 年多个顶会（CVPR, ICCV, ECCV, ICLR, ICML, MICCAI, NeurIPS）的论文统计时间序列，
按类别（pretrain, segmentation, generation, multimodal, medical 等）聚合成了 JSON：

{trend_json}

说明：
- years: [2021, 2022, ...]
- total_papers: 每年总论文数
- by_category: 每个类别，对应 2021–2025 每年的论文数量列表

⚠️ 特别注意：
- 所有统计都基于 **DBLP 的论文收录数据**，  
  可能会漏掉少数论文或有个别收录偏差，但对这些顶会来说已经覆盖绝大多数论文，**非常适合看整体趋势**。  
  可以在文案里用轻松的方式提到这一点（比如“就当是顶会圈的气象台数据”）。
- 如果某个方向的 key 是 "other"，它只是一个“杂项桶”，在分析主要趋势时不要把它当主角，可以顺带提到但不用重点展开。

请你写出 **1 条适合发在小红书上的趋势文案**，内容是：
“站在 2025 年，回头看 2021–2025 顶会方向演化 + 对 2026 的预测”。

### 风格要求
- 中文为主，少量英文术语
- 语气轻松、好玩、像 Papergent 在跟读者聊天，不要学术 review 口吻
- 明确的时间视角：**2025 年的现在，回顾过去五年，并往 2026 往前看**。
- 总长度控制在 **400–700 字**，可以分 4–7 段短话
- 不要用 Markdown 标题（#），也不要 1.2.3 这种学术大纲

### 内容要点（整条文案大致结构）

1. **开头人设 + 总体趋势一句话（2025 视角）**  
   - 第一行可以是类似：“五年顶会论文趋势一图看完 📈 谁在狂飙，谁在退场？（来自 2025 的回看）”  
   - 下一句用第一人称介绍自己和时间视角：  
     “大家好，我是中科大苏研院 Miracle Lab 的 Papergent，现在站在 2025 年，帮你把 2021–2025 这波 AI 顶会热潮整体过一遍。”

2. **数据来源的说明（DBLP）**  
   - 用 1–2 句交代：  
     “所有数据来自 DBLP 的论文收录统计，不是官方排行榜，但对 CVPR/ICLR/NeurIPS 等顶会来说已经覆盖了绝大多数论文，用来看大盘趋势非常靠谱。”  
   - 可以加一句轻松的类比，比如“就当是 AI 顶会圈过去五年的天气记录”。

3. **核心方向的趋势速写（从 2025 回头看）**  
   - 挑 4–6 个你认为最关键的方向（比如 pretrain/self_supervised、generation、multimodal、medical、robustness、3D 等），  
     用非常口语的方式概括它们在 2021–2025 的走势：  
     - 谁是一路狂飙的“顶流方向”（可以描述成“从小众变成所有人都得卷一卷”）、  
     - 谁是一直稳稳在线的“老牌打工人”、  
     - 谁是最近两年突然蹿起来的“黑马”。  
   - 不需要给出精确数字，但要体现相对涨跌和量级感，可以用“从每年几十篇涨到上百篇”这种定性描述。  
   - 如果合理，可以顺带点出 few-shot / robustness / domain adaptation 这种“虽然不是最大盘，但很关键”的支线方向。

4. **2026 及之后 3 年的轻量预测（2025 往前看）**  
   - 用 1–2 段说：  
     - 哪 2–3 个方向大概率继续超高热度（比如 pretraining、多模态、大模型相关），  
     - 哪些方向会进入“论文很多但创意开始同质化”的平台期，  
     - Papergent 自己最看好的 1–2 个交叉方向（例如“多模态 + 医疗”、“3D + 自动驾驶”、“robustness + 安全”等），  
       以 2025 的视角解释一下为什么看好。  
   - 语气保持是预测而不是断言，可以用“我自己的感觉是…”、“大概率会…”来弱化绝对感。

5. **给选题/择业的读者一点直观建议 + 互动**  
   - 用 1 小段告诉大家：  
     - “如果你喜欢卷基础理论 / 算法，可以往哪几个方向看；  
        如果更想做落地应用，可以关注哪些赛道；  
        想做冷门宝藏，也可以从哪些增长快但体量不大的方向里选。”  
   - 最后抛一个问题：“从这五年的趋势里，你觉得自己应该站在哪个赛道上？你现在的方向，是顺风车还是逆风盘？”  
   - 加上 4–8 个 hashtag，例如：  
     #AI趋势 #顶会论文 #CVPR #NeurIPS #科研方向 #2026预测 #Papergent

### Emoji 使用
- 全文使用大约 5–12 个 emoji，分布在不同句子里
- 常用的可以是：📈📉📊🤖🧠🔥✨🚗🩻🌊🌈 等

### 输出格式
- 只输出一条完整文案
- 直接给我可以复制到小红书里的文本，不要解释你的分析过程，也不要带 JSON

请根据上述要求和给定的 2021–2025 统计数据，**以 2025 年的视角生成这条趋势+预测文案**。
"""
    return prompt




# ============ 通用 LLM 调用 ============

def call_llm(prompt: str, max_retries: int = 5) -> str:
    """调用 OpenRouter Chat API，带 429 限流重试。"""
    if not LLM_API_KEY:
        raise RuntimeError(
            "未设置 LLM_API_KEY，请先在 shell 中 export LLM_API_KEY='你的OpenRouter key'。"
        )

    url = LLM_API_BASE.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        # 这两个 header 可选
        # "HTTP-Referer": "https://your-site-or-github",
        # "X-Title": "ai-conference-trend-analyzer",
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个擅长阅读大规模论文统计数据并撰写学术趋势报告的助手。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    for attempt in range(1, max_retries + 1):
        resp = requests.post(url, headers=headers, json=payload, timeout=120)

        # 429：限流，打印提示，然后重试
        if resp.status_code == 429:
            print(f"\n[LLM WARN] 收到 429 限流（第 {attempt}/{max_retries} 次尝试）")
            try:
                print("[LLM WARN BODY]:", resp.text[:500])
            except Exception:
                pass

            if attempt == max_retries:
                resp.raise_for_status()

            # 简单指数回退，避免一直打爆同一个模型
            sleep_secs = 5 * attempt
            print(f"[LLM WARN] 暂停 {sleep_secs} 秒后重试同一次请求...")
            time.sleep(sleep_secs)
            continue

        if resp.status_code != 200:
            print("\n[LLM ERROR] status =", resp.status_code)
            print("[LLM ERROR BODY]:")
            print(resp.text[:1000])
            resp.raise_for_status()

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    raise RuntimeError("LLM 请求多次重试后仍然失败")




def save_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ============ 可视化（做得更适合社媒） ============

def plot_year_category_bars(
    year_stats: Dict[int, dict], out_dir: str = "figs/year_bars"
):
    """
    For each year, draw a horizontal bar chart of top-N categories (English labels only),
    with a more modern palette and denser layout for social-media style.
    """
    os.makedirs(out_dir, exist_ok=True)

    for year, info in year_stats.items():
        cat_stats = info["category_stats"]
        items = [(cat, s["count"]) for cat, s in cat_stats.items() if s["count"] > 0]
        if not items:
            continue

        # sort by count desc, take top 12
        items.sort(key=lambda x: x[1], reverse=True)
        top_items = items[:12]
        cats = [c for c, _ in top_items]
        counts = np.array([n for _, n in top_items], dtype=int)

        labels = [CATEGORY_LABELS_EN.get(c, c) for c in cats]
        y_pos = np.arange(len(counts))

        # nice multi-hue palette
        base_cmap = plt.cm.get_cmap("viridis")
        colors = base_cmap(np.linspace(0.15, 0.9, len(counts)))

        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111)

        bars = ax.barh(
            y_pos,
            counts,
            color=colors,
            height=0.6,
            edgecolor="#ffffff",
            linewidth=0.8,
        )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.set_xlabel("Number of Papers")
        ax.set_title(f"{year} · Top 12 Research Directions", pad=14)

        # only vertical gridlines for a cleaner look
        ax.xaxis.grid(True)
        ax.yaxis.grid(False)

        # remove top/right spines, keep bottom/left very light
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color("#DDDDDD")

        max_count = counts.max()
        for bar, cnt in zip(bars, counts):
            x = bar.get_width()
            y = bar.get_y() + bar.get_height() / 2
            ax.text(
                x + max_count * 0.01,
                y,
                f"{int(cnt)}",
                va="center",
                ha="left",
                fontsize=9,
                color="#333333",
            )

        fig.tight_layout()
        out_path = os.path.join(out_dir, f"year_{year}_top_categories.png")
        fig.savefig(out_path, dpi=320)
        plt.close(fig)
        print(f"[OK] Saved figure: {out_path}")




def plot_trend_lines(trend_data: dict, out_dir: str = "figs/trends"):
    """
    Plot time-series trends (2021–2025) for several key directions:
    1) multi-line chart
    2) stacked area chart
    All labels are in English to avoid encoding issues.
    """
    os.makedirs(out_dir, exist_ok=True)
    years = trend_data["years"]

    focus_cats = [
        "pretrain",
        "generation",
        "multimodal",
        "three_d",
        "video",
        "medical",
        "robustness",
    ]

    # ===== multi-line chart =====
    plt.figure(figsize=(10, 6))
    colors = plt.cm.Set2(np.linspace(0, 1, len(focus_cats)))

    for i, cat in enumerate(focus_cats):
        if cat not in trend_data["by_category"]:
            continue
        counts = trend_data["by_category"][cat]
        label = CATEGORY_LABELS_EN.get(cat, cat)
        plt.plot(
            years,
            counts,
            marker="o",
            linewidth=2.3,
            color=colors[i],
            label=label,
        )

    plt.title("Key Directions: Paper Count Trends (2021–2025)", fontsize=14, pad=12)
    plt.xlabel("Year", fontsize=11)
    plt.ylabel("Number of Papers", fontsize=11)
    plt.xticks(years)
    plt.legend(loc="upper left", fontsize=9, frameon=True, framealpha=0.9)
    plt.tight_layout()

    out_path = os.path.join(out_dir, "trend_focus_multi_lines.png")
    plt.savefig(out_path, dpi=260)
    plt.close()
    print(f"[OK] Saved trend line figure: {out_path}")

    # ===== stacked area chart (robust version) =====
    valid_labels = []
    series_list = []
    for cat in focus_cats:
        if cat not in trend_data["by_category"]:
            continue
        series_list.append(trend_data["by_category"][cat])
        valid_labels.append(CATEGORY_LABELS_EN.get(cat, cat))

    if series_list:
        lengths = [len(s) for s in series_list]
        T = min(min(lengths), len(years))
        if T == 0:
            print("[WARN] No data for stacked area in plot_trend_lines.")
            return

        if len(set(lengths)) != 1 or T != len(years):
            print(
                f"[WARN] trend_lines series length mismatch: "
                f"min={min(lengths)}, max={max(lengths)}, years_len={len(years)}; "
                f"using first {T} points."
            )

        years_plot = years[:T]
        data = np.row_stack(
            [np.array(s[:T], dtype=float) for s in series_list]
        )

        colors_area = plt.cm.Set3(np.linspace(0, 1, data.shape[0]))

        plt.figure(figsize=(10, 6))
        plt.stackplot(years_plot, data, labels=valid_labels, colors=colors_area, alpha=0.9)
        plt.title("Key Directions: Stacked Area (2021–2025)", fontsize=14, pad=12)
        plt.xlabel("Year", fontsize=11)
        plt.ylabel("Number of Papers (stacked)", fontsize=11)
        plt.xticks(years_plot)
        plt.legend(loc="upper left", fontsize=9, frameon=True, framealpha=0.9)
        plt.tight_layout()

        out_path = os.path.join(out_dir, "trend_focus_stack_area.png")
        plt.savefig(out_path, dpi=260)
        plt.close()
        print(f"[OK] Saved stacked area figure: {out_path}")


def save_cover_image_prompt(path: str = "figs/cover_image_prompt.txt") -> None:
    """
    1. 保存一段给人看的中文封面插画 prompt；
    2. 如果配置了图像生成 API，则：
       - IMAGE_BACKEND=hf  -> 调 Hugging Face router + SDXL
       - IMAGE_BACKEND=openrouter -> 调 OpenRouter（保持原逻辑）
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # ===== 人类阅读版（中文，写文件用）=====
    human_prompt = """
画一张竖版 4:5 比例的漫画风插画，用于小红书封面。

画面要素：
- 中央角色：一个拟人化的小纸人机器人 Papergent，表情聪明又有点呆萌，戴着眼镜或头戴式耳机，手里抱着一摞论文。
- 论文封面上可以隐约看到几个英文单词：CVPR、ICCV、ECCV、ICLR、ICML、MICCAI、NeurIPS。
- 背景：有一些半透明的统计图表元素，比如折线图、柱状图、堆叠面积图、热力图，颜色柔和，不要太抢戏。
- 整体风格：简洁、明亮、科技感但不冰冷，偏二次元 / 扁平插画风，适合小红书封面。
- 配色：偏粉紫 + 蓝色系，可以点缀少量黄色或绿色，营造轻松但专业的感觉。
- 构图：上方和下方尽量留出一些干净空间，方便后期叠加中文标题文字。

禁止：
- 不要画出具体的真实人物、logo 或敏感内容。
- 不要出现过于复杂的背景细节，保持整体简洁。

请输出一张高分辨率、线条清晰的插画。
""".strip()

    with open(path, "w", encoding="utf-8") as f:
        f.write(human_prompt)
    print(f"[OK] Saved (human) cover image prompt to {path}")

    # ===== 模型专用版（英文关键词，给 SDXL / 其他 text2img 吃）=====
    model_prompt = (
        "vertical 4:5 manga style illustration, clean and simple, "
        "a small chibi paper robot character named Papergent, "
        "wearing big round glasses and large over-ear headphones, "
        "sitting on a pile of research papers and books, holding an open paper. "
        "around the character there are many flying papers, sticky notes and tabs, "
        "with clear text on the covers such as CVPR, ICCV, ECCV, ICLR, ICML, MICCAI, NeurIPS. "
        "in the background there are a few soft, semi-transparent data visuals: "
        "a line chart, a bar chart, a stacked area chart and a heatmap window. "
        "overall look is cute, modern and nerdy, comic / anime style, "
        "with balanced pleasant colors (not dominated by a single color), "
        "high resolution, sharp clean line art, designed as a social media cover image."
    )


    negative_prompt = (
        "no realistic human, no ancient painting, no traditional hanfu clothes, "
        "no classical chinese man, no landscape, no mountains, no pine trees, "
        "no dark muddy colors, no calligraphy, no oil painting style"
    )

    backend = os.getenv("IMAGE_BACKEND", IMAGE_BACKEND).lower()

    # ====================== 方案 A：Hugging Face Router ======================
    if backend == "hf":
        if not HF_API_TOKEN:
            print("[IMG WARN] HF_API_TOKEN not set; only saved text prompt.")
            return

        model_id = HF_IMAGE_MODEL
        url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
        headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": "application/json",
        }
        # 4:5 比例，稍微高一点分辨率，适合小红书封面
        payload = {
            "inputs": model_prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
                "width": 896,     # 4:5 -> 896x1120
                "height": 1120,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            },
            "options": {"wait_for_model": True},
        }

        print(f"[IMG] Requesting cover image from HuggingFace router: {model_id}")
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=300)
            print(f"[IMG] HTTP status: {resp.status_code}")

            if resp.status_code != 200:
                print("[IMG ERROR] body:")
                print(resp.text[:800])
                if resp.status_code == 403:
                    print(
                        "[IMG HINT] 403 Forbidden：当前 HF_API_TOKEN 没有调用 Inference 的权限。\n"
                        "请到 https://huggingface.co/settings/tokens 重新创建一个带 Inference/API 权限的 token，\n"
                        "然后在服务器上： export HF_API_TOKEN='hf_xxx' 再跑一次。"
                    )
                resp.raise_for_status()

            img_bytes = resp.content
            out_img_path = os.path.join(os.path.dirname(path), "cover_image.png")
            with open(out_img_path, "wb") as f_img:
                f_img.write(img_bytes)

            print(f"[OK] Saved cover image to {out_img_path}")

        except Exception as e:
            print(f"[IMG ERROR] Failed to generate cover image via HF: {e}")

        return

    # ====================== 方案 B：OpenRouter（保持原逻辑） ======================
    if backend == "openrouter":
        base = os.getenv("LLM_API_BASE", "https://openrouter.ai/api/v1")
        key = os.getenv("LLM_API_KEY", "")
        image_model = os.getenv("LLM_IMAGE_MODEL", "").strip()

        if not key or not image_model:
            print(
                "[WARN] LLM_API_KEY 或 LLM_IMAGE_MODEL 未设置，"
                "只保存了文字 prompt，没有生成封面图片。"
            )
            return

        url = base.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": image_model,
            "messages": [{"role": "user", "content": model_prompt}],
            "modalities": ["image", "text"],
            "image_config": {"aspect_ratio": "4:5"},
            "max_output_images": 1,
        }

        print(f"[IMG] Requesting cover image from OpenRouter model: {image_model}")
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            print(f"[IMG] HTTP status: {resp.status_code}")
            if resp.status_code != 200:
                print("[IMG ERROR] body:")
                print(resp.text[:800])
                resp.raise_for_status()

            data = resp.json()
            choice = data["choices"][0]["message"]
            images = choice.get("images")
            if not images:
                print("[IMG WARN] API 返回中没有 images 字段，可能是模型不支持图片生成或参数不正确。")
                return

            img_info = images[0]["image_url"]["url"]
            if not img_info.startswith("data:image"):
                print("[IMG WARN] 收到的 image_url 不是 data URL，暂时不解析：", img_info[:80])
                return

            header, b64_data = img_info.split(",", 1)
            img_bytes = base64.b64decode(b64_data)

            out_img_path = os.path.join(os.path.dirname(path), "cover_image.png")
            with open(out_img_path, "wb") as f_img:
                f_img.write(img_bytes)

            print(f"[OK] Saved cover image to {out_img_path}")

        except Exception as e:
            print(f"[IMG ERROR] Failed to generate cover image via OpenRouter: {e}")

        return

    # ====================== 未识别 backend ======================
    print(
        f"[IMG INFO] IMAGE_BACKEND='{backend}' 未识别，"
        "目前只支持 'hf' 或 'openrouter'，本次只保存了文字 prompt。"
    )



def plot_category_share_stacked_area(
    trend_data: dict,
    top_k: int = 6,
    out_dir: str = "figs/stacked_share",
):
    """
    画 2021–2025 方向占比演化（stacked area）。

    修正版：
    - 先检查每个类别的时间序列长度，取最短长度 T；
    - years 也截到前 T 年；
    - 每个类别都截到前 T 个点，保证 row_stack 时所有行长度一致；
    - main_cats 只从非 "other" 类别里选，"other" 行统一表示“除了 top_k 以外的所有类别”。
    """
    os.makedirs(out_dir, exist_ok=True)

    years = list(trend_data["years"])
    by_cat = trend_data["by_category"]

    # 各类别的时间序列长度
    lengths = [len(v) for v in by_cat.values() if hasattr(v, "__len__")]
    if not lengths:
        print("[WARN] No category data for stacked area plot.")
        return

    # 统一使用的时间长度 T
    T = min(min(lengths), len(years))
    if T == 0:
        print("[WARN] Empty time axis for stacked area plot.")
        return

    if len(set(lengths)) != 1 or T != len(years):
        print(
            f"[WARN] category series length mismatch: "
            f"min={min(lengths)}, max={max(lengths)}, years_len={len(years)}; "
            f"using first {T} points for all."
        )

    # 截断年份 & 每个类别的计数序列
    years = years[:T]
    by_cat_trimmed = {
        cat: list(counts)[:T]
        for cat, counts in by_cat.items()
        if hasattr(counts, "__len__")
    }

    # 只在非 "other" 里选 top_k 主角
    total_per_cat = {
        cat: int(sum(counts))
        for cat, counts in by_cat_trimmed.items()
        if cat != "other" and sum(counts) > 0
    }
    if not total_per_cat:
        print("[WARN] No non-zero main categories for stacked area plot.")
        return

    sorted_cats = sorted(total_per_cat.items(), key=lambda kv: kv[1], reverse=True)
    main_cats = [c for c, _ in sorted_cats[:top_k]]
    other_cats = [c for c in by_cat_trimmed.keys() if c not in main_cats]

    print("[STACKED] main categories:", main_cats)
    print("[STACKED] other bucket contains:", other_cats)

    num_years = len(years)
    K = len(main_cats) + 1  # 再加一个“other”
    data = np.zeros((K, num_years), dtype=float)

    # 逐年计算占比
    for t in range(num_years):
        total_tags = sum(by_cat_trimmed[c][t] for c in by_cat_trimmed)
        if total_tags == 0:
            continue

        # 主类占比
        for idx, c in enumerate(main_cats):
            val = by_cat_trimmed[c][t]
            data[idx, t] = val / total_tags

        # 其他类别占比
        other_val = sum(by_cat_trimmed[c][t] for c in other_cats)
        data[-1, t] = other_val / total_tags

    labels = main_cats + ["other"]
    label_names = [
        CATEGORY_LABELS_EN.get(
            c,
            "Other / Long-tail" if c == "other" else c,
        )
        for c in labels
    ]

    print("[STACKED] data shape:", data.shape)  # (K, T)

    # -------- 这里是新的配色方案 --------
    # 前 top_k 个主类：使用一个偏蓝绿、比较柔和的 colormap
    num_main = len(main_cats)
    cmap_main = plt.cm.get_cmap("PuBuGn")
    main_colors = cmap_main(np.linspace(0.35, 0.9, num_main))

    # 最后的 "other"：用很浅的中性灰，降低存在感，不再是大块亮黄色
    other_color = np.array([[0.90, 0.90, 0.93, 1.0]])  # RGBA
    colors = np.vstack([main_colors, other_color])
    # ---------------------------------

    plt.figure(figsize=(10, 6))
    plt.stackplot(years, data, labels=label_names, colors=colors, alpha=0.95)
    plt.title("Research Direction Share Over Time", fontsize=14, pad=12)
    plt.xlabel("Year", fontsize=11)
    plt.ylabel("Share of Category Tags", fontsize=11)
    plt.xticks(years)
    plt.legend(loc="upper left", fontsize=9, frameon=True, framealpha=0.9)
    plt.tight_layout()

    out_path = os.path.join(out_dir, "category_share_2021_2025.png")
    plt.savefig(out_path, dpi=260)
    plt.close()
    print(f"[OK] Saved stacked area figure: {out_path}")



def plot_category_leaderboards(
    trend_data: dict,
    top_n_total: int = 10,
    top_n_growth: int = 8,
    min_total_for_growth: int = 30,
    out_dir: str = "figs/category_leaderboards",
):
    """
    两张图：
    1) 2021–2025 累积论文数 Top-N 的方向
    2) 增长倍率 Top-N 的黑马方向
    """
    os.makedirs(out_dir, exist_ok=True)
    years = trend_data["years"]
    by_cat = trend_data["by_category"]
    first_idx = 0
    last_idx = len(years) - 1

    total_per_cat = {
        cat: int(sum(counts)) for cat, counts in by_cat.items() if sum(counts) > 0
    }
    if not total_per_cat:
        print("[WARN] No category data for leaderboards.")
        return

    # --- 1) total count leaderboard ---
    sorted_total = sorted(total_per_cat.items(), key=lambda kv: kv[1], reverse=True)
    top_total = sorted_total[:top_n_total]

    cats_total = [c for c, _ in top_total]
    counts_total = np.array([n for _, n in top_total], dtype=int)
    labels_total = [CATEGORY_LABELS_EN.get(c, c) for c in cats_total]

    fig1 = plt.figure(figsize=(11, 6))
    ax1 = fig1.add_subplot(111)

    cmap_total = plt.cm.get_cmap("Blues")
    colors = cmap_total(np.linspace(0.35, 0.9, len(counts_total)))
    y_pos = np.arange(len(counts_total))

    bars = ax1.barh(
        y_pos,
        counts_total,
        color=colors,
        height=0.7,
        edgecolor="#FFFFFF",
        linewidth=0.9,
    )

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels_total)
    ax1.set_xlabel("Number of Papers (2021–2025)")
    ax1.set_title("Top Directions by Total Paper Count", pad=14)
    ax1.xaxis.grid(True)
    ax1.yaxis.grid(False)

    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)

    max_count = counts_total.max()
    for bar, cnt in zip(bars, counts_total):
        x = bar.get_width()
        y = bar.get_y() + bar.get_height() / 2
        ax1.text(
            x + max_count * 0.01,
            y,
            f"{int(cnt)}",
            va="center",
            ha="left",
            fontsize=9,
            color="#333333",
        )

    fig1.tight_layout()
    out_path1 = os.path.join(out_dir, "top_total_categories.png")
    fig1.savefig(out_path1, dpi=320)
    plt.close(fig1)
    print(f"[OK] Saved total leaderboard: {out_path1}")

    # --- 2) growth leaderboard ---
    growth_info = []
    for cat, counts in by_cat.items():
        total = int(sum(counts))
        if total < min_total_for_growth:
            continue
        start = counts[first_idx]
        end = counts[last_idx]
        ratio = (end + 1) / (start + 1)
        growth_info.append((cat, ratio, start, end, total))

    if not growth_info:
        print("[WARN] No category with enough total for growth leaderboard.")
        return

    growth_sorted = sorted(growth_info, key=lambda x: x[1], reverse=True)
    top_growth = growth_sorted[:top_n_growth]

    cats_g = [c for c, _, _, _, _ in top_growth]
    ratios_g = np.array([r for _, r, _, _, _ in top_growth], dtype=float)
    labels_g = [CATEGORY_LABELS_EN.get(c, c) for c in cats_g]

    fig2 = plt.figure(figsize=(11, 6))
    ax2 = fig2.add_subplot(111)

    cmap_growth = plt.cm.get_cmap("Greens")
    colors_g = cmap_growth(np.linspace(0.35, 0.9, len(ratios_g)))
    x_pos = np.arange(len(ratios_g))

    bars = ax2.bar(
        x_pos,
        ratios_g,
        color=colors_g,
        width=0.65,
        edgecolor="#FFFFFF",
        linewidth=0.9,
    )

    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(labels_g, rotation=30, ha="right")
    ax2.set_ylabel("Growth Factor (2025 vs 2021)")
    ax2.set_title("Dark Horse Directions by Growth Factor", pad=14)
    ax2.yaxis.grid(True)
    ax2.xaxis.grid(False)

    for spine in ["top", "right"]:
        ax2.spines[spine].set_visible(False)

    for x, bar, ratio in zip(x_pos, bars, ratios_g):
        h = bar.get_height()
        ax2.text(
            x,
            h + 0.15,
            f"×{ratio:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#333333",
        )

    fig2.tight_layout()
    out_path2 = os.path.join(out_dir, "top_growth_categories.png")
    fig2.savefig(out_path2, dpi=320)
    plt.close(fig2)
    print(f"[OK] Saved growth leaderboard: {out_path2}")


def compute_conf_category_matrix(
    df_all: pd.DataFrame,
    focus_cats: List[str],
) :
    """
    返回 (conferences, categories, matrix)，其中 matrix[i, j] 是
    conference i 在 category j 上的论文数（2021–2025 累计）。
    """
    conferences = sorted(df_all["conference"].dropna().astype(str).unique().tolist())
    cats = focus_cats

    mat = np.zeros((len(conferences), len(cats)), dtype=int)

    for i, conf in enumerate(conferences):
        df_c = df_all[df_all["conference"] == conf]
        for j, cat_key in enumerate(cats):
            col_name = f"is_{cat_key}"
            if col_name in df_c.columns:
                mat[i, j] = int(df_c[col_name].sum())
            else:
                mat[i, j] = 0

    return conferences, cats, mat

def plot_conf_category_heatmap(df_all: pd.DataFrame, out_dir: str = "figs/conf_category"):
    """
    Conference × Direction heatmap
    - 使用清新一点的蓝绿系配色
    - 取消网格线，整体更干净
    - 在格子里标数字
    """
    os.makedirs(out_dir, exist_ok=True)

    conferences, cats, mat = compute_conf_category_matrix(df_all, FOCUS_CATS_FOR_CONF)
    if mat.size == 0:
        print("[WARN] Empty matrix for conf-category heatmap.")
        return

    cat_labels = [CATEGORY_LABELS_EN.get(c, c) for c in cats]

    fig = plt.figure(figsize=(11, 6))
    ax = fig.add_subplot(111)

    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#F6F7FB")

    # 先取一个 YlGnBu，然后截取比较“清淡”的中高亮区，避免太黑太土
    base_cmap = plt.cm.get_cmap("YlGnBu", 256)
    light_colors = base_cmap(np.linspace(0.25, 0.95, 256))  # 0~1 里截掉最深的那段
    fresh_cmap = LinearSegmentedColormap.from_list("fresh_ylgnbu", light_colors)

    im = ax.imshow(mat, aspect="auto", cmap=fresh_cmap)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Paper Count")

    ax.set_xticks(np.arange(len(cats)))
    ax.set_xticklabels(cat_labels, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(conferences)))
    ax.set_yticklabels(conferences)

    ax.set_title("Conference × Direction Heatmap (2021–2025 total)", pad=16, fontsize=18, weight="bold")

    # 不要轴网格线，热图自己就是网格
    ax.grid(False)

    # 在每个格子里写数字（小一点）
    vmax = mat.max() if mat.max() > 0 else 1
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            val = mat[i, j]
            if val == 0:
                continue
            # 深色块用浅字，浅色块用深字
            color_text = "#FFFFFF" if val > vmax * 0.6 else "#222222"
            ax.text(
                j,
                i,
                str(val),
                ha="center",
                va="center",
                fontsize=9,
                color=color_text,
            )

    # 去掉粗边框
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.tight_layout()
    out_path = os.path.join(out_dir, "conf_category_heatmap.png")
    fig.savefig(out_path, dpi=320)
    plt.close(fig)
    print(f"[OK] Saved conf-category heatmap: {out_path}")



def plot_conf_category_bubble(df_all: pd.DataFrame, out_dir: str = "figs/conf_category"):
    os.makedirs(out_dir, exist_ok=True)

    conferences, cats, mat = compute_conf_category_matrix(df_all, FOCUS_CATS_FOR_CONF)
    if mat.size == 0:
        print("[WARN] Empty matrix for conf-category bubble plot.")
        return

    cat_labels = [CATEGORY_LABELS_EN.get(c, c) for c in cats]
    fig = plt.figure(figsize=(11, 6))
    ax = fig.add_subplot(111)

    max_count = mat.max() if mat.max() > 0 else 1
    sizes = (mat / max_count) * 1500  # bigger for social media

    # 用一个暖色系调色板，填充+深色描边
    cmap = plt.cm.get_cmap("Oranges")

    for i, conf in enumerate(conferences):
        for j, cat_key in enumerate(cats):
            if mat[i, j] == 0:
                continue
            color = cmap(0.35 + 0.55 * mat[i, j] / max_count)
            ax.scatter(
                j,
                i,
                s=sizes[i, j],
                alpha=0.8,
                color=color,
                edgecolors="#333333",
                linewidths=0.4,
            )

    ax.set_xticks(np.arange(len(cats)))
    ax.set_xticklabels(cat_labels, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(conferences)))
    ax.set_yticklabels(conferences)

    ax.set_xlabel("Direction")
    ax.set_ylabel("Conference")
    ax.set_title("Conference × Direction Bubble Map (2021–2025 total)", pad=14)

    ax.grid(True, linestyle="--", alpha=0.3)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    out_path = os.path.join(out_dir, "conf_category_bubble.png")
    fig.savefig(out_path, dpi=320)
    plt.close(fig)
    print(f"[OK] Saved conf-category bubble plot: {out_path}")



def plot_conference_radar(df_all: pd.DataFrame, out_dir: str = "figs/conf_radar"):
    """
    For each conference draw a radar chart over a few key directions.
    Cleaner style: light background, no crowded radial tick labels.
    """
    os.makedirs(out_dir, exist_ok=True)

    conferences = sorted(df_all["conference"].dropna().astype(str).unique().tolist())
    cats = RADAR_CATS

    conf_cat_counts = {conf: [] for conf in conferences}
    cat_max = {c: 0 for c in cats}

    for conf in conferences:
        df_c = df_all[df_all["conference"] == conf]
        for cat_key in cats:
            col_name = f"is_{cat_key}"
            val = int(df_c[col_name].sum()) if col_name in df_c.columns else 0
            conf_cat_counts[conf].append(val)
            cat_max[cat_key] = max(cat_max[cat_key], val)

    for c in cat_max:
        if cat_max[c] == 0:
            cat_max[c] = 1

    num_vars = len(cats)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    labels = [CATEGORY_LABELS_EN.get(c, c) for c in cats]

    for conf in conferences:
        raw_vals = conf_cat_counts[conf]
        values_norm = [
            raw_vals[i] / cat_max[cats[i]] if cat_max[cats[i]] > 0 else 0.0
            for i in range(num_vars)
        ]
        values_norm += values_norm[:1]

        fig = plt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111, polar=True)

        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#F6F7FB")

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=9)

        # 不要一堆半径刻度标签，只保留网格线
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels([])
        ax.set_ylim(0, 1.0)

        ax.grid(color="#D6DAE6", linestyle="--", linewidth=0.8, alpha=0.8)

        ax.plot(
            angles,
            values_norm,
            linewidth=2.2,
            linestyle="-",
            color="#FF7F50",
        )
        ax.fill(angles, values_norm, alpha=0.35, color="#FFB18A")

        ax.set_title(f"{conf}: Direction Profile (relative)", fontsize=12, pad=16)

        fig.tight_layout()
        safe_conf = conf.replace("/", "_").replace(" ", "_")
        out_path = os.path.join(out_dir, f"radar_{safe_conf}.png")
        fig.savefig(out_path, dpi=260)
        plt.close(fig)
        print(f"[OK] Saved radar for {conf}: {out_path}")


def setup_matplotlib_style():
    """
    Global matplotlib style:
    - light, slightly tinted background (not pure white)
    - modern sans-serif font
    - soft grids & legends
    """
    plt.style.use("default")

    matplotlib.rcParams.update({
        # figure
        "figure.facecolor": "#FFFFFF",
        "figure.dpi": 140,
        # axes
        "axes.facecolor": "#F6F7FB",
        "axes.edgecolor": "#E0E0E0",
        "axes.linewidth": 1.0,
        "axes.grid": True,
        "grid.color": "#E1E4EE",
        "grid.linestyle": "--",
        "grid.alpha": 0.6,
        # font
        "font.family": "DejaVu Sans",  # 基本所有 Linux 都有
        "axes.titlesize": 16,
        "axes.titleweight": "semibold",
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        # legend
        "legend.frameon": True,
        "legend.framealpha": 0.95,
        "legend.facecolor": "#FFFFFF",
        "legend.edgecolor": "#E0E0E0",
    })



# ============ 主流程 ============

def main():
    setup_matplotlib_style()
    # 1. 读取所有 CSV
    df_all = load_all_papers()

    # 2. 构建每一年的统计信息
    year_stats = build_yearly_stats(df_all)

    # 3. 构建多年的趋势数据
    trend_data = build_trend_data(year_stats)

    # 4. 画图（本地可视化）
    plot_year_category_bars(year_stats)          # 原来的年度 top 类别柱状图（如果你还保留）
    plot_trend_lines(trend_data)                 # 原来的趋势折线图（可选）
    plot_category_share_stacked_area(trend_data) # 新：方向占比演化
    plot_category_leaderboards(trend_data)       # 新：卷王榜（总量 + 增长倍率）
    plot_conf_category_heatmap(df_all)           # 新：会议×方向热力图
    plot_conf_category_bubble(df_all)            # 新：会议×方向气泡图
    plot_conference_radar(df_all)                # 新：会议人设雷达图
    save_cover_image_prompt()                    # 新：生成封面插画 prompt

    # 5. 调用大模型做每一年的总结（小红书文案）
    for year, info in year_stats.items():
        prompt = make_year_prompt(year, info)
        print(f"[LLM] 正在生成 {year} 年的总结……")
        content = call_llm(prompt)
        out_path = os.path.join("llm_reports", f"year_{year}_summary.md")
        save_text(out_path, content)
        print(f"[OK] 保存 {year} 年总结到 {out_path}")

    # 6. 调用大模型做 2021–2025 整体趋势 + 2026 预测（小红书文案）
    trend_prompt = make_trend_prompt(trend_data)
    print("[LLM] 正在生成 2021–2025 整体趋势分析和 2026 预测……")
    trend_content = call_llm(trend_prompt)
    save_text("llm_reports/trend_2021_2025_and_forecast.md", trend_content)
    print("[OK] 保存整体趋势报告到 llm_reports/trend_2021_2025_and_forecast.md")



if __name__ == "__main__":
    main()
