import json
import os
import requests
import dashscope
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
from dashscope import ImageSynthesis
import argparse

from schedule2prompt import single_day_schedule_to_prompt

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'


def generate_daily_schedule_images(
    schedule_json,
    conference,
    year,
    output_dir="./daily_schedules",
    city=None
):
    os.makedirs(output_dir, exist_ok=True)

    with open(schedule_json, "r", encoding="utf-8") as f:
        full_schedule = json.load(f)

    api_key = os.getenv("DASHSCOPE_API_KEY")

    for day, day_schedule in full_schedule.items():
        print(f"🎨 正在生成 {day} 的日程海报...")

        prompt = single_day_schedule_to_prompt(
            day=day,
            day_schedule=day_schedule,
            conference=conference,
            year=year,
            city=city
        )
        # print(prompt)

        rsp = ImageSynthesis.call(
            api_key=api_key,
            model="qwen-image-plus",
            prompt=prompt,
            n=1,
            size="1328*1328",
            prompt_extend=True,
            watermark=False
        )

        # print('response: %s' % rsp)
        
        if rsp.status_code != HTTPStatus.OK:
            print(f"❌ {day} 生成失败")
            continue

        for result in rsp.output.results:
            file_name = PurePosixPath(
                unquote(urlparse(result.url).path)
            ).parts[-1]

            save_path = os.path.join(
                output_dir,
                f"{conference}_{year}_{day}.png"
            )

            with open(save_path, "wb+") as f:
                f.write(requests.get(result.url).content)

            print(f"✅ 已生成：{save_path}")


# if __name__ == "__main__":
#     generate_daily_schedule_images(
#         schedule_json="cvpr_2025_my_schedule.json",
#         conference="CVPR",
#         year=2025,
#         city="Nashville"
#     )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render daily conference schedule images"
    )

    parser.add_argument(
        "--schedule_json",
        type=str,
        default="agent_part2/your_personalized_schedule.json",
        help="Path to personalized schedule JSON"
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
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Conference city (optional)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="agent_part2/daily_schedules",
        help="Directory to save generated images"
    )

    args = parser.parse_args()

    generate_daily_schedule_images(
        schedule_json=args.schedule_json,
        conference=args.conference,
        year=args.year,
        city=args.city,
        output_dir=args.output_dir
    )