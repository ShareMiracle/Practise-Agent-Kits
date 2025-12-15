#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
一键跑全流程：

1. crawl_topconfs_dblp.py
   - 从 DBLP 抓取各顶会 2021–2025 论文，写入 data_dblp/*.csv

2. analyze_ai_confs_with_llm.py
   - 读 CSV，画所有图，调用 LLM 生成 year_xxx.md 和 trend_xxx.md

3. xhs_publisher.py
   - 调用 export_all_notes()，把所有文案 + 图片打包到 xhs_exports/ 下
"""

import time
import traceback


def run_step(idx: int, desc: str, func):
    """带一点日志的统一封装。"""
    print("\n" + "=" * 72)
    print(f"[STEP {idx}] {desc}")
    print("=" * 72)
    t0 = time.time()
    try:
        func()
    except Exception as e:
        print(f"\n[STEP {idx} ERROR] {desc} 失败：{e}")
        traceback.print_exc()
        raise
    else:
        elapsed = time.time() - t0
        print(f"\n[STEP {idx} DONE] {desc} 结束，耗时 {elapsed:.1f} 秒")


def main():
    # 延迟导入，避免没用到的模块也初始化
    from crawl_topconfs_dblp import main as crawl_main       # step 1 :contentReference[oaicite:0]{index=0}
    from analyze_ai_confs_with_llm import main as analyze_main  # step 2 :contentReference[oaicite:1]{index=1}
    from xhs_publisher import export_all_notes                # step 3 :contentReference[oaicite:2]{index=2}

    t_all = time.time()

    # 1. 抓 DBLP + 写 CSV
    run_step(1, "抓取 DBLP 并生成 data_dblp/*.csv", crawl_main)

    # 2. 分析 + 画图 + 调 LLM 生成 llm_reports/*
    run_step(2, "分析 CSV、画图、生成 llm_reports 文案", analyze_main)

    # 3. 打包所有小红书素材到 xhs_exports/*
    run_step(3, "打包全部小红书素材包（xhs_exports）", export_all_notes)

    total = time.time() - t_all
    print("\n" + "=" * 72)
    print("[ALL DONE] 全流程执行完毕 ✅")
    print(f"总耗时 {total:.1f} 秒")
    print("现在可以去 xhs_exports/ 里挑选你要发的小红书素材包了～")
    print("=" * 72)


if __name__ == "__main__":
    main()
