# Step 1
# python agent_part1/agent_part1_contacts.py \
#   --conference CVPR \
#   --keywords registration self-supervised 3d \
#   --user_name Jason \
#   --user_research "self-supervised 3D registration and medical image analysis" 

# Step 2
# python agent_part2/fetch_schedule.py --conference CVPR --year 2025
# python agent_part2/personalize_schedule.py --conference CVPR --year 2025 --keywords registration self-supervised 3d
# python agent_part2/render_schedule_image.py --conference CVPR --year 2025 --city Nashville

# Step 3
# python agent_part3/part3_agent.py --conference CVPR --year 2025 --city Nashville

# Step 4
# python agent_part4/part4_agent.py \
#   --user_name "Jason" \
#   --user_research "Self-supervised learning for medical image analysis" \
#   --conference CVPR \
#   --year 2025 \
#   --your_focus "Focus on self-supervised learning and medical imaging sessions." 

#!/bin/bash
set -e

# ================================
# 🔧 用户只需要改这里
# ================================

CONFERENCE="CVPR"
YEAR=2025
CITY="Nashville"

KEYWORDS="registration self-supervised 3d"

USER_NAME="Jason"
USER_RESEARCH="self-supervised 3D registration and medical image analysis"

FOCUS_SUMMARY="Focus on self-supervised learning and medical imaging sessions."

# ================================
# 📁 输出路径统一管理
# ================================

# PART1_OUT="outputs/${CONFERENCE,,}_${YEAR}_contacts.json"
# PART2_SCHEDULE_JSON="outputs/${CONFERENCE,,}_${YEAR}_schedule.json"
# PART3_OUT="outputs/${CONFERENCE,,}_${YEAR}_city_guide.json"

# ================================
# Step 1: 学术联系人 & Coffee Chat
# ================================

echo "🚀 Step 1: Finding contacts & generating emails..."

python agent_part1/agent_part1_contacts.py \
  --conference "$CONFERENCE" \
  --keywords $KEYWORDS \
  --user_name "$USER_NAME" \
  --user_research "$USER_RESEARCH"

# ================================
# Step 2: 会议日程 → 个性化 → 日程图
# ================================

echo "📅 Step 2.1: Fetching conference schedule..."
python agent_part2/fetch_schedule.py \
  --conference "$CONFERENCE" \
  --year "$YEAR"

echo "🧠 Step 2.2: Generating personalized schedule..."
python agent_part2/personalize_schedule.py \
  --conference "$CONFERENCE" \
  --year "$YEAR" \
  --keywords "$KEYWORDS"

echo "🎨 Step 2.3: Rendering daily schedule images..."
python agent_part2/render_schedule_image.py \
  --conference "$CONFERENCE" \
  --year "$YEAR" \
  --city "$CITY"

# ================================
# Step 3: 城市 & 场馆 & 美食景点
# ================================

echo "🌍 Step 3: Generating city guide..."
python agent_part3/part3_agent.py \
  --conference "$CONFERENCE" \
  --year "$YEAR" \
  --city "$CITY"

# ================================
# Step 4: 小红书图文生成
# ================================

echo "📸 Step 4: Generating Xiaohongshu post..."

python agent_part4/part4_agent.py \
  --user_name "$USER_NAME" \
  --user_research "$USER_RESEARCH" \
  --conference "$CONFERENCE" \
  --year "$YEAR" \
  --your_focus "$FOCUS_SUMMARY" \

echo ""
echo "🎉 ALL DONE!"
echo "📄 小红书文案：outputs/xhs_post.txt"
echo "🖼️ 图片：outputs/xhs_images/"