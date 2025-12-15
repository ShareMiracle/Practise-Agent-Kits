import os
import requests
from bs4 import BeautifulSoup
import argparse

CONFERENCE_SCHEDULE_URLS = {
    ("CVPR", 2025): "https://cvpr.thecvf.com/virtual/2025/calendar",
    ("NeurIPS", 2025): "https://neurips.cc/virtual/2025/loc/san-diego/calendar",
    ("MICCAI", 2025): "https://conferences.miccai.org/2025/en/default.asp",
    ("ICCV", 2025): "https://iccv.thecvf.com/virtual/2025/calendar",
    ("ICLR", 2025): "https://iclr.cc/virtual/2025/calendar",
    ("ICML", 2025): "https://icml.cc/virtual/2025/calendar",
    ("NeurIPS", 2025): "https://neurips.cc/virtual/2025/loc/san-diego/calendar",
}

SAVE_DIR = "agent_part2/schedule_data"
os.makedirs(SAVE_DIR, exist_ok=True)


def fetch_and_save_schedule(conference, year):
    url = CONFERENCE_SCHEDULE_URLS.get((conference, year))
    if not url:
        raise ValueError("❌ 未配置该会议的日程 URL")

    print(f"🌐 抓取 {conference} {year} 官网日程...")

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )
    response.raise_for_status()

    # 1️⃣ 保存原始 HTML（最重要）
    html_path = os.path.join(
        SAVE_DIR, f"{conference}_{year}_raw.html"
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"✅ 原始 HTML 已保存：{html_path}")

    # 2️⃣ 可选：生成一个干净文本，方便 debug / quick view
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 5]

    txt_path = os.path.join(
        SAVE_DIR, f"{conference}_{year}_clean.txt"
    )
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"📝 清洗文本已保存：{txt_path}")

    return html_path, txt_path


# if __name__ == "__main__":
#     # fetch_and_save_schedule("CVPR", 2025)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch and save conference schedule HTML"
    )

    parser.add_argument(
        "--conference",
        type=str,
        required=True,
        help="Conference name, e.g. CVPR"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Conference year, e.g. 2025"
    )

    args = parser.parse_args()

    fetch_and_save_schedule(
        conference=args.conference,
        year=args.year
    )