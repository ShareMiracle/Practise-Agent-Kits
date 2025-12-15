import requests
import time
import os
import csv
from typing import Dict, List

# ===================== 基础配置 =====================

DBLP_PUBL_API = "https://dblp.org/search/publ/api"

# 需要爬的会议 & 在 DBLP 里的 BHT 命名模式
CONFERENCES = {
    # 单卷会议：一个 year 对应一个 BHT
    "CVPR": {
        "type": "single",
        "pattern": "db/conf/cvpr/cvpr{year}.bht",
    },
    "ICCV": {
        "type": "single",
        "pattern": "db/conf/iccv/iccv{year}.bht",
    },
    "ICLR": {
        "type": "single",
        "pattern": "db/conf/iclr/iclr{year}.bht",
    },
    "ICML": {
        "type": "single",
        "pattern": "db/conf/icml/icml{year}.bht",
    },
    "NeurIPS": {
        # NeurIPS 在 DBLP 里的路径是 nips/neuripsYYYY
        "type": "single",
        "pattern": "db/conf/nips/neurips{year}.bht",
    },
    # 多卷会议：同一年有很多 part（-1, -2, …）
    "ECCV": {
        "type": "multi",
        "pattern": "db/conf/eccv/eccv{year}-{index}.bht",
        "max_volumes": 30,  # 循环 1..max_volumes，遇到空卷就停
    },
    "MICCAI": {
        "type": "multi",
        "pattern": "db/conf/miccai/miccai{year}-{index}.bht",
        "max_volumes": 20,
    },
}

# 年份范围（你可以改，比如只想 2021~2024）
YEARS = list(range(2021, 2026))

# ===================== 类别 & 关键词 =====================

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    # ---------- 训练范式 / 模型规模 ----------
    "pretrain": [
        "pre-train", "pretrain", "pretraining", "pre-training",
        "pre-trained", "pretrained",
        "foundation model", "foundation models",
        "large language model", "large-language model", " llm ", " llms ",
        "large vision model", "large-scale model", "large scale model",
        "vision-language model", "vlm",
        "scaling law", "scaling laws",
    ],
    "self_supervised": [
        "self-supervised", "self supervised", "self supervision",
        "unsupervised pre-training", "unsupervised pretraining",
        "contrastive learning", "contrastive loss",
        "masked autoencoder", "masked image modeling",
        "masked modeling", " mae ", " mae-", " mim ",
        "simclr", "byol", "moco", "moco v2", "swav",
        "simsiam", "barlow twins", "dino", "dino v2", "dinov2",
        "i-jepa", "representation learning", " ssl ",
    ],

    # ---------- 典型视觉任务 ----------
    "segmentation": [
        "segmentation", "segmenter", "segmentation network",
        "panoptic segmentation", "semantic segmentation",
        "instance segmentation", "lesion segmentation",
        "organ segmentation", "tumor segmentation", "tumour segmentation",
    ],
    "detection": [
        "detection", "detector", "detecting",
        "object detection", "face detection", "anomaly detection",
        "change detection", "event detection",
    ],
    "classification": [
        "classification", "classifying", "classifier",
        "recognition", "recognizing", "identification",
        "image recognition", "action recognition",
        "activity recognition",
    ],
    "generation": [
        "generation", "generative", "image synthesis",
        "text-to-image", "text to image",
        "image-to-image", "image to image",
        "video-to-video", "video to video",
        "style transfer", "image editing",
        "diffusion model", "diffusion models", "diffusion-based",
        "denoising diffusion", "score-based model",
        "gan ", "gan-", "gan-based", "generative adversarial network",
        " vae ", " variational autoencoder",
    ],
    "reconstruction": [
        "reconstruction", "reconstructing",
        "tomographic reconstruction", "ct reconstruction",
        "mr reconstruction", "mri reconstruction",
        "compressed sensing", "inverse problem",
        "super-resolution", "super resolution", "sr network",
        "deconvolution",
    ],
    "registration": [
        "registration", "image registration",
        "deformable registration", "non-rigid registration",
        "rigid registration", "slice-to-volume registration",
    ],
    "tracking": [
        "tracking", "tracker",
        "object tracking", "multi-object tracking",
        "visual tracking", "trajectory prediction",
        "motion forecasting", "motion prediction",
    ],
    "pose": [
        "pose estimation", "human pose", "3d pose",
        "2d pose", "keypoint detection", "key-point detection",
        "landmark detection", "hand pose", "body pose", "skeleton",
    ],
    "video": [
        "video ", "video-based", "video based",
        "video understanding", "video analysis",
        "temporal action", "video segmentation",
        "video object segmentation", "vos ",
        "video captioning", "video generation",
    ],
    "three_d": [
        " 3d ", " 3-d", " three-dimensional",
        "point cloud", "point clouds",
        "mesh reconstruction", "surface reconstruction",
        "neural radiance field", "neural radiance fields",
        " nerf", " nerfs",
        "implicit surface", "implicit representation",
        "multi-view stereo", "multi view stereo", " mvs ",
        "depth estimation", "monocular depth", "stereo matching",
        "stereo depth", "scene reconstruction",
        " slam ", "structure from motion", " sfm ",
    ],
    "multimodal": [
        "multimodal", "multi-modal", "vision-language",
        "vision and language", "image-text", "text-image",
        "cross-modal", "cross modal",
        "image captioning", " captioning", "visual question answering",
        " vqa ", "vision-language model", " vlm ",
        "referring expression", "phrase grounding",
        "visual grounding", "video-language",
    ],

    # ---------- 学习设定 / 泛化 / 可靠性 ----------
    "fewshot": [
        "few-shot", "few shot",
        "zero-shot", "zero shot",
        "one-shot", "one shot",
        "low-shot", "low shot",
        "n-shot", "-shot learning", "shot learning",
        "meta-learning", "meta learning", "meta-learner", "meta learner",
    ],
    "semi_supervised": [
        "semi-supervised", "semi supervised", "semi-supervision",
        "weakly-supervised", "weakly supervised", "weak supervision",
        "pseudo label", "pseudo-label", "pseudo labels", "pseudo-labels",
        "noisy labels", "label noise", "limited labels",
        "incomplete labels", "few labels", "unlabeled data",
        "unsupervised learning",
    ],
    "domain_adaptation": [
        "domain adaptation", "unsupervised domain adaptation",
        " uda ", "cross-domain", "cross domain",
        "domain generalization", "out-of-domain",
        "domain shift",
    ],
    "robustness": [
        "robustness", "robust ",
        "adversarial attack", "adversarial example",
        "adversarial training", "adversarial defense",
        "adversarial robustness",
        "out-of-distribution", "out of distribution", " ood ",
        "distribution shift", "covariate shift",
        "corruption", "corrupted",
        "certified robustness", "certified defense",
        "fairness", " bias ", "de-bias", "debiasing",
        "privacy", "differential privacy", "membership inference",
    ],

    # ---------- 模型类型 ----------
    "graph": [
        "graph neural network", "graph convolutional network",
        "graph convolution", " gcn ", " gat ", " gnn ",
        "message passing", "graph attention", "graph learning",
        "spatio-temporal graph",
    ],
    "rl": [
        "reinforcement learning", "deep reinforcement learning",
        " rl ", "markov decision process", " mdp ",
        "policy gradient", "actor-critic", "actor critic",
        "q-learning", "q learning", "value iteration",
        "policy optimization",
    ],
    "transformer": [
        "transformer", "vision transformer", " vit ",
        "swin transformer", " swin ", " deit",
        "multi-head attention", "multihead attention",
        "self-attention", "self attention",
    ],

    # ---------- 应用领域 ----------
    "medical": [
        "medical image", "medical imaging", "bio-medical", "biomedical",
        "computed tomography", "ct scan", "ct imaging",
        " mri ", "magnetic resonance", "pet/ct", "pet-ct",
        "ultrasound", "sonography",
        "x-ray", "xray", "radiograph", "radiography",
        "fundus", "retinal", "histopathology", "pathology",
        "microscopy", "dermatology", "lesion", "tumor", "tumour",
        "organ-at-risk", "organ at risk",
        "radiotherapy", "radiation therapy", "radiomics",
    ],
    "autonomous_driving": [
        "autonomous driving", "self-driving", "self driving",
        "autonomous vehicle", "autonomous vehicles",
        "lane detection", "lane keeping", "lane segmentation",
        "traffic sign", "traffic light", "ego vehicle",
        " bev ", "bird's-eye-view", "bird's eye view",
    ],
    "nlp": [
        "natural language processing", "language model",
        "text classification", "machine translation",
        "question answering", " qa ", "named entity recognition",
        " ner ", "language understanding",
    ],
}


# ===================== DBLP 抓取函数 =====================

def fetch_dblp_toc_entries(bht_key: str,
                           page_size: int = 300,
                           max_hits: int = 10000,
                           max_retries: int = 5) -> List[dict]:
    """
    调 DBLP publication search API，把一个 BHT（一个卷的 TOC）里所有条目抓出来。
    加入了：
      - 更小的 page_size (300) 减少单次压力
      - 每次请求之间固定 sleep
      - 遇到 429 时的退避重试
    返回：dblp info 字典列表。
    """
    entries: List[dict] = []
    offset = 0
    session = requests.Session()

    while offset < max_hits:
        params = {
            "q": f"toc:{bht_key}:",
            "h": page_size,
            "f": offset,
            "format": "json",
        }

        attempt = 0
        while True:
            attempt += 1
            try:
                resp = session.get(DBLP_PUBL_API, params=params, timeout=30)
                # 如果被限流（429）
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after is not None:
                        try:
                            wait_sec = int(retry_after) + 1
                        except ValueError:
                            wait_sec = 10
                    else:
                        # 指数退避：5s, 15s, 30s, ...
                        wait_sec = 5 * attempt
                    print(f"[WARN] DBLP 429 Too Many Requests for {bht_key} "
                          f"(offset={offset}), 等待 {wait_sec} 秒后重试 (第 {attempt} 次)...")
                    time.sleep(wait_sec)
                    if attempt >= max_retries:
                        print(f"[ERROR] {bht_key} offset={offset} 多次 429，放弃这个 offset 段")
                        return entries
                    continue

                # 其它 HTTP 错误直接抛出
                resp.raise_for_status()
                break  # 正常拿到数据，退出重试循环

            except requests.HTTPError as e:
                # 非 429 的 HTTP 错误直接往外抛，交给上层处理
                raise
            except requests.RequestException as e:
                # 网络类错误，也退避重试一下
                if attempt >= max_retries:
                    print(f"[ERROR] 网络错误 {e}，多次重试失败，放弃 {bht_key} offset={offset}")
                    return entries
                wait_sec = 5 * attempt
                print(f"[WARN] 网络错误 {e}，等待 {wait_sec} 秒后重试 {bht_key} offset={offset} (第 {attempt} 次)...")
                time.sleep(wait_sec)

        data = resp.json()
        hits_obj = data.get("result", {}).get("hits", {})
        hit_list = hits_obj.get("hit", [])

        if isinstance(hit_list, dict):
            hit_list = [hit_list]
        if not hit_list:
            break

        for hit in hit_list:
            info = hit.get("info", {})
            entries.append(info)

        if len(hit_list) < page_size:
            break

        offset += page_size
        # 固定节流，避免触发限流
        time.sleep(1.5)

    return entries


def fetch_conf_year_entries(conf_short: str,
                            year: int,
                            conf_cfg: dict) -> List[dict]:
    """
    对某个会议 + 某一年，基于配置里的 BHT pattern 去 DBLP 抓这一年所有论文。
    返回：dblp info 字典列表。
    """
    conf_type = conf_cfg["type"]
    pattern = conf_cfg["pattern"]

    all_entries: List[dict] = []

    if conf_type == "single":
        bht = pattern.format(year=year)
        print(f"[INFO] {conf_short} {year} -> BHT = {bht}")
        entries = fetch_dblp_toc_entries(bht)
        print(f"[INFO] {conf_short} {year} 从 {bht} 抓到 {len(entries)} 篇")
        all_entries.extend(entries)

    elif conf_type == "multi":
        max_volumes = conf_cfg.get("max_volumes", 20)
        print(f"[INFO] {conf_short} {year} 多卷会议，最多尝试 {max_volumes} 个卷")
        found_any = False
        for idx in range(1, max_volumes + 1):
            bht = pattern.format(year=year, index=idx)
            entries = fetch_dblp_toc_entries(bht)
            if not entries:
                if found_any:
                    print(f"[INFO] {conf_short} {year} 卷 {idx} 为空，认为卷到此结束")
                    break
                else:
                    print(f"[WARN] {conf_short} {year} 卷 {idx} ({bht}) 没找到任何条目")
                    continue
            found_any = True
            print(f"[INFO] {conf_short} {year} 卷 {idx} ({bht}) 抓到 {len(entries)} 篇")
            all_entries.extend(entries)
            time.sleep(0.1)

        print(f"[INFO] {conf_short} {year} 总共抓到 {len(all_entries)} 篇（多卷合计）")
    else:
        raise ValueError(f"未知会议类型: {conf_type}")

    return all_entries


# ===================== 分类 & CSV =====================

def classify_title(title: str) -> Dict[str, bool]:
    """
    用关键词做多标签分类。
    """
    text = " " + (title or "").lower() + " "
    flags: Dict[str, bool] = {}

    for cat, keywords in CATEGORY_KEYWORDS.items():
        flags[cat] = any(kw in text for kw in keywords)

    flags["other"] = not any(flags.values())
    return flags


def make_row(conf_short: str, year: int, info: dict) -> Dict[str, str]:
    """
    把 DBLP 的 info 字典转换成一行 CSV 记录。
    """
    title = info.get("title", "") or ""
    dblp_year = str(info.get("year", "") or "")
    venue = info.get("venue", "") or ""
    doi = info.get("doi", "") or ""
    ee = info.get("ee", "") or ""   # electronic edition / url
    key = info.get("key", "") or ""

    authors_field = info.get("authors", {})
    authors_str = ""
    if isinstance(authors_field, dict) and "author" in authors_field:
        authors_obj = authors_field["author"]
        if isinstance(authors_obj, list):
            names = []
            for a in authors_obj:
                if isinstance(a, dict):
                    names.append(a.get("text", ""))
                else:
                    names.append(str(a))
            authors_str = "; ".join([n for n in names if n])
        elif isinstance(authors_obj, dict):
            authors_str = authors_obj.get("text", "")
        else:
            authors_str = str(authors_obj)

    flags = classify_title(title)
    categories = [k for k, v in flags.items() if v]
    categories_str = ";".join(categories)

    row: Dict[str, str] = {
        "conference": conf_short,
        "year_target": str(year),
        "year_dblp": dblp_year,
        "title": title,
        "venue": venue,
        "authors": authors_str,
        "doi": doi,
        "ee_url": ee,
        "dblp_key": key,
        "categories": categories_str,
    }

    for cat in CATEGORY_KEYWORDS.keys():
        row[f"is_{cat}"] = str(int(flags.get(cat, False)))
    row["is_other"] = str(int(flags.get("other", False)))

    return row


def save_csv(conf_short: str, rows: List[Dict[str, str]], out_dir: str = "data_dblp") -> None:
    """
    把某个会议的所有记录写到一个 CSV 里：data_dblp/CONF_2021_2025_dblp.csv
    """
    if not rows:
        print(f"[WARN] {conf_short} 没有任何记录，不生成 CSV")
        return

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{conf_short}_2021_2025_dblp.csv")

    fieldnames = [
        "conference",
        "year_target",
        "year_dblp",
        "title",
        "venue",
        "authors",
        "doi",
        "ee_url",
        "dblp_key",
        "categories",
    ]
    for cat in CATEGORY_KEYWORDS.keys():
        fieldnames.append(f"is_{cat}")
    fieldnames.append("is_other")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] 写出 CSV: {out_path} (共 {len(rows)} 行)")


# ===================== 主流程 =====================

def main():
    for conf_short, conf_cfg in CONFERENCES.items():
        print(f"\n========== {conf_short} ==========")
        conf_rows: List[Dict[str, str]] = []

        for year in YEARS:
            print(f"[INFO] 准备抓取 {conf_short} {year} ...")
            try:
                entries = fetch_conf_year_entries(conf_short, year, conf_cfg)
            except requests.HTTPError as e:
                print(f"[ERROR] {conf_short} {year} HTTP 错误: {e}")
                continue
            except Exception as e:
                print(f"[ERROR] {conf_short} {year} 失败: {e}")
                continue

            for info in entries:
                conf_rows.append(make_row(conf_short, year, info))

        save_csv(conf_short, conf_rows)


if __name__ == "__main__":
    main()
