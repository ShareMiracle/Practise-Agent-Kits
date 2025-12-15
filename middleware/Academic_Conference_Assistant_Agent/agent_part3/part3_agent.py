import json
from fetch_conference_venue import fetch_conference_venue
from recommend_places import recommend_restaurants_and_attractions
import os
import argparse

def run_part3(conference, year, city, output_path):
    print("📍 查询会议举办地与场馆...")
    venue_info_json = fetch_conference_venue(conference, year, city)
    venue_info = json.loads(venue_info_json)

    print("🍜 推荐餐厅 & 景点...")
    places_json = recommend_restaurants_and_attractions(
        city=venue_info["city"],
        venue=venue_info["venue"],
        address=venue_info["address"]
    )
    places = json.loads(places_json)

    result = {
        **venue_info,
        **places
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ Part3 输出已保存：{output_path}")
    return result


# if __name__ == "__main__":
#     run_part3(
#         conference="CVPR",
#         year=2025,
#         output_path="outputs/cvpr_2025_city_guide.json"
#     )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch conference venue and recommend nearby places"
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
        required=True,
        help="Conference city, e.g. Nashville"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="agent_part3/city_tour_guide.json",
        help="Output JSON path"
    )

    args = parser.parse_args()

    run_part3(
        conference=args.conference,
        year=args.year,
        city=args.city,
        output_path=args.output
    )