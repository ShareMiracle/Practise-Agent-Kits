import os
import json
from generate_xhs_text import generate_xhs_post
from generate_xhs_images import generate_xhs_image, build_xhs_four_grid_prompt
import argparse

def run_part4(
    user_name,
    user_research,
    conference,
    year,
    part1_path,
    part2_summary,
    part3_path
):
    with open(part1_path, "r", encoding="utf-8") as f:
        part1_contacts = json.load(f)

    with open(part3_path, "r", encoding="utf-8") as f:
        part3_city_guide = json.load(f)

    print("✍️ 生成小红书文案...")
    text = generate_xhs_post(
        user_name=user_name,
        user_research=user_research,
        conference=conference,
        year=year,
        part1_contacts=part1_contacts,
        part2_schedule_summary=part2_summary,
        part3_city_guide=part3_city_guide
    )

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/xhs_post.txt", "w", encoding="utf-8") as f:
        f.write(text)

    print("🖼️ 生成配图...")
    img_path = generate_xhs_image(
        prompt=build_xhs_four_grid_prompt(
        conference=conference,
        city=part3_city_guide["city"],
        venue=part3_city_guide["venue"]
    ),
        output_dir="outputs/xhs_images"
    )

    print("✅ Part4 完成")
    print("📄 文案：outputs/xhs_post.txt")
    print("🖼️ 图片：", img_path)


# if __name__ == "__main__":
#     run_part4(
#         user_name="Siyan",
#         user_research="Self-supervised learning for medical image analysis",
#         conference="CVPR",
#         year=2025,
#         part1_path="/home/zhuosiyan/AAAgent/agent_part1/agent_part1_output.json",
#         part2_summary="Focus on self-supervised learning and medical imaging sessions.",
#         part3_path="/home/zhuosiyan/AAAgent/agent_part3/outputs/cvpr_2025_city_guide.json"
#     )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Xiaohongshu conference post (text + image)"
    )

    parser.add_argument("--user_name", type=str, required=True)
    parser.add_argument("--user_research", type=str, required=True)
    parser.add_argument("--conference", type=str, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--part1", type=str, default="agent_part1/coffee_chat_email.json", help="Path to Part1 JSON")
    parser.add_argument(
        "--your_focus",
        type=str,
        default="Focus on self-supervised learning and medical imaging sessions.",
        help="Short summary of personalized schedule"
    )
    parser.add_argument("--part3", type=str, default="agent_part3/city_tour_guide.json", help="Path to Part3 JSON")
    args = parser.parse_args()

    run_part4(
        user_name=args.user_name,
        user_research=args.user_research,
        conference=args.conference,
        year=args.year,
        part1_path=args.part1,
        part2_summary=args.your_focus,
        part3_path=args.part3
    )