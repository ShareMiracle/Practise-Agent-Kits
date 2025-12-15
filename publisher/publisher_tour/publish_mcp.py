from mcp.server.fastmcp import FastMCP
import os
import sys
from typing import List, Dict, Any

# Ensure repo root is on sys.path (supports `python publisher/publish_mcp.py`)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# 导入旅游数据工具
try:
    from crawler.places_read_mcp import get_spots_by_city
except ImportError:
    # Fallback for package execution contexts
    from crawler.places_read_mcp import get_spots_by_city

mcp = FastMCP("Xiaohongshu Publisher")


@mcp.tool(
    name='validate_xiaohongshu_content',
    description='审核小红书发布内容，确保符合平台规范（标题≤20字，内容≤800字，标签≤4个）'
)
def validate_xiaohongshu_content(
    title: str,
    content: str,
    topics: List[str]
) -> Dict[str, Any]:
    """
    审核小红书发布内容
    
    参数:
        title: 笔记标题
        content: 笔记内容
        topics: 话题标签列表
    
    返回:
        审核结果，包括是否通过、问题说明和修改建议
    """
    issues = []
    suggestions = {}
    
    # 检查标题长度（不超过20个字）
    title_length = len(title)
    if title_length > 20:
        issues.append(f"标题过长：{title_length}字（限制20字）")
        suggestions["title"] = title[:20]
    
    # 检查内容长度（不超过800字）
    content_length = len(content)
    if content_length > 800:
        issues.append(f"内容过长：{content_length}字（限制800字）")
        suggestions["content"] = content[:797] + "..."
    
    # 检查标签数量（不超过4个）
    topics_count = len(topics)
    if topics_count > 4:
        issues.append(f"标签过多：{topics_count}个（限制4个）")
        suggestions["topics"] = topics[:4]
    
    # 检查标签格式
    invalid_topics = [t for t in topics if not t.startswith('#')]
    if invalid_topics:
        issues.append(f"标签格式错误：{invalid_topics}（应以#开头）")
        suggestions["topics_fixed"] = ['#' + t.lstrip('#') for t in topics]
    
    is_valid = len(issues) == 0
    
    return {
        "valid": is_valid,
        "message": "内容审核通过" if is_valid else "内容需要修改",
        "issues": issues,
        "suggestions": suggestions,
        "stats": {
            "title_length": title_length,
            "title_limit": 20,
            "content_length": content_length,
            "content_limit": 800,
            "topics_count": topics_count,
            "topics_limit": 4
        }
    }


@mcp.tool(
    name='publish_xiaohongshu_video',
    description='发布视频笔记到小红书（需已登录会话；建议先用 validate_xiaohongshu_content 审核标题/内容/标签）'
)
def publish_xiaohongshu_video(
    file_path: str,
    title: str,
    content: str,
    topics: List[str] = None,
    schedule_hours: int = 24
) -> Dict[str, Any]:
    """
    发布视频笔记到小红书
    
    参数:
        file_path: 视频文件的绝对路径
        title: 笔记标题
        content: 笔记内容描述
        topics: 话题标签列表，如 ["#旅游", "#攻略"]
        schedule_hours: 定时发布的小时数（默认24小时后）
    
    返回:
        发布结果信息
    """
    try:
        # Import locally to avoid requiring selenium if not used
        from middleware.upload_utils import publish_single_post, get_driver, xiaohongshu_login
        
        if topics is None:
            topics = ["#旅游", "#攻略", "#景点推荐"]
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"文件不存在: {file_path}"
            }
        
        driver = get_driver()
        try:
            xiaohongshu_login(driver)
            publish_single_post(
                driver=driver,
                file_path=file_path,
                title=title,
                content=content,
                topics=topics,
                date_offset_hours=schedule_hours
            )
            
            return {
                "success": True,
                "message": "视频笔记发布成功",
                "details": {
                    "file_path": file_path,
                    "title": title,
                    "topics": topics,
                    "schedule_hours": schedule_hours
                }
            }
        finally:
            driver.quit()
            
    except ImportError as e:
        return {
            "success": False,
            "message": f"缺少依赖: {str(e)}，请确保已安装 selenium"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"发布失败: {str(e)}"
        }


@mcp.tool(
    name='publish_xiaohongshu_images',
    description='发布图文笔记到小红书（需已登录会话；建议先用 validate_xiaohongshu_content 审核；注意提供绝对路径）'
)
def publish_xiaohongshu_images(
    file_path: str,
    title: str,
    content: str,
    topics: List[str] = None,
    schedule_hours: int = 0
) -> Dict[str, Any]:
    """
    发布图文笔记到小红书
    
    参数:
        file_path: 图片文件的绝对路径（支持多图，用逗号分隔）
        title: 笔记标题
        content: 笔记内容描述
        topics: 话题标签列表，如 ["#旅游", "#攻略"]
        schedule_hours: 定时发布的小时数（默认立刻发送）
    
    返回:
        发布结果信息
    """
    try:
        from middleware.upload_utils import publish_image_post, get_driver, xiaohongshu_login
        
        if topics is None:
            topics = ["#旅游", "#风景", "#打卡"]
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"文件不存在: {file_path}"
            }
        
        driver = get_driver()
        try:
            xiaohongshu_login(driver)
            publish_image_post(
                driver=driver,
                file_path=file_path,
                title=title,
                content=content,
                topics=topics,
                date_offset_hours=schedule_hours
            )
            
            return {
                "success": True,
                "message": "图文笔记发布成功",
                "details": {
                    "file_path": file_path,
                    "title": title,
                    "topics": topics,
                    "schedule_hours": schedule_hours
                }
            }
        finally:
            driver.quit()
            
    except ImportError as e:
        return {
            "success": False,
            "message": f"缺少依赖: {str(e)}，请确保已安装 selenium"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"发布失败: {str(e)}"
        }


@mcp.tool(
    name='generate_xiaohongshu_content',
    description='根据景点信息生成小红书笔记内容（自动收敛：标题≤20字、内容≤800字、标签≤4个）'
)
def generate_xiaohongshu_content(
    province: str,
    city: str,
    spot_name: str = None,
    style: str = "旅游攻略"
) -> Dict[str, Any]:
    """
    根据景点信息生成小红书笔记内容
    
    参数:
        province: 省份名称
        city: 城市名称
        spot_name: 特定景点名称（可选，如果不指定则生成城市概览）
        style: 内容风格，如 "旅游攻略", "Vlog", "美食探店", "打卡分享"
    
    返回:
        生成的标题、内容和推荐话题
    """
    data = get_spots_by_city(province, city)
    spots = data.get("spots", [])
    
    if not spots:
        return {
            "success": False,
            "message": f"未找到 {city}, {province} 的景点数据"
        }
    
    # 如果指定了景点名称，只使用该景点
    if spot_name:
        spots = [s for s in spots if spot_name in s.get("name", "")]
        if not spots:
            return {
                "success": False,
                "message": f"未找到景点: {spot_name}"
            }
    
    # 选择评分最高的景点
    top_spots = sorted(
        spots,
        key=lambda x: float(x.get("rating", 0)),
        reverse=True
    )[:3]
    
    # 生成内容
    if style == "旅游攻略":
        title = f"🌟{city}必去景点！{len(top_spots)}个宝藏打卡地分享✨"
        content = f"📍{city}旅游攻略来啦！\n\n"
        
        for i, spot in enumerate(top_spots, 1):
            content += f"{i}️⃣ {spot.get('name', '未知景点')}\n"
            content += f"⭐️ 评分: {spot.get('rating', 'N/A')}\n"
            if spot.get('是否免费'):
                content += "💰 免费景点！\n"
            content += "\n"
        
        content += f"💡小贴士：建议游玩{len(top_spots)}天，慢慢感受{city}的魅力~\n"
        content += f"\n#去哪儿旅行 #{city}旅游 #旅游攻略"
        
        topics = [f"#{city}旅游", "#旅游攻略", "#景点推荐", "#打卡"]
        
    elif style == "Vlog":
        title = f"🎬{city}Vlog | 探索{len(top_spots)}个绝美景点！"
        content = f"📹今天带大家逛{city}！\n\n"
        content += f"这次打卡了{len(top_spots)}个超美的地方：\n\n"
        
        for i, spot in enumerate(top_spots, 1):
            content += f"📍{spot.get('name', '未知景点')}\n"
        
        content += f"\n每一个都超级出片！\n"
        content += f"喜欢的宝子们记得点赞收藏哦~\n"
        content += f"\n#{city}vlog #旅行vlog #城市探索"
        
        topics = [f"#{city}vlog", "#旅行vlog", "#vlog日常", "#探店"]
        
    elif style == "打卡分享":
        title = f"✨{city}打卡|这些地方真的太美了！"
        content = f"📸{city}打卡合集来咯~\n\n"
        
        for spot in top_spots:
            content += f"📍{spot.get('name', '未知景点')}\n"
        
        content += f"\n随手一拍都是大片！\n"
        content += f"姐妹们赶紧安排起来💕\n"
        content += f"\n#{city}打卡 #旅行分享 #周末去哪儿"
        
        topics = [f"#{city}打卡", "#打卡", "#旅行分享", "#周末游"]
    
    else:
        title = f"{city}旅游 | {top_spots[0].get('name', '景点')}超值得！"
        content = f"推荐{city}的{len(top_spots)}个好地方！\n\n"
        topics = [f"#{city}", "#旅游", "#推荐"]
    
    # 自动审核和修正内容
    # 标题限制20字
    if len(title) > 20:
        title = title[:20]
    
    # 内容限制800字
    if len(content) > 800:
        content = content[:797] + "..."
    
    # 话题限制4个
    if len(topics) > 4:
        topics = topics[:4]
    
    # 确保话题格式正确
    topics = ['#' + t.lstrip('#') for t in topics]
    
    return {
        "success": True,
        "title": title,
        "content": content,
        "topics": topics,
        "spots_included": [s.get("name") for s in top_spots],
        "style": style
    }


@mcp.tool(
    name='batch_publish_xiaohongshu',
    description='批量发布小红书笔记（支持多个城市的景点内容）'
)
def batch_publish_xiaohongshu(
    province: str,
    cities: List[str],
    file_paths: List[str],
    style: str = "旅游攻略",
    schedule_interval_hours: int = 24
) -> Dict[str, Any]:
    """
    批量生成并发布小红书笔记
    
    参数:
        province: 省份名称
        cities: 城市列表
        file_paths: 对应每个城市的媒体文件路径列表
        style: 内容风格
        schedule_interval_hours: 每篇笔记之间的发布间隔（小时）
    
    返回:
        批量发布结果
    """
    if len(cities) != len(file_paths):
        return {
            "success": False,
            "message": "城市数量与文件数量不匹配"
        }
    
    results = []
    
    for i, (city, file_path) in enumerate(zip(cities, file_paths)):
        # 生成内容
        content_result = generate_xiaohongshu_content(province, city, style=style)
        
        if not content_result.get("success"):
            results.append({
                "city": city,
                "success": False,
                "message": content_result.get("message")
            })
            continue
        
        # 计算发布时间
        schedule_hours = schedule_interval_hours * (i + 1)
        
        # 判断文件类型
        is_video = file_path.lower().endswith(('.mp4', '.mov', '.avi'))
        
        # 发布
        if is_video:
            publish_result = publish_xiaohongshu_video(
                file_path=file_path,
                title=content_result["title"],
                content=content_result["content"],
                topics=content_result["topics"],
                schedule_hours=schedule_hours
            )
        else:
            publish_result = publish_xiaohongshu_images(
                file_path=file_path,
                title=content_result["title"],
                content=content_result["content"],
                topics=content_result["topics"],
                schedule_hours=schedule_hours
            )
        
        results.append({
            "city": city,
            "success": publish_result.get("success"),
            "title": content_result["title"],
            "schedule_hours": schedule_hours,
            "message": publish_result.get("message")
        })
    
    success_count = sum(1 for r in results if r.get("success"))
    
    return {
        "success": True,
        "total": len(results),
        "success_count": success_count,
        "failed_count": len(results) - success_count,
        "results": results
    }


if __name__ == "__main__":
    import sys
    
    if "--sse" in sys.argv or os.getenv("MCP_TRANSPORT") == "sse":
        print("🚀 启动 Xiaohongshu Publisher MCP 服务器 (SSE模式)")
        print("   服务名称: Xiaohongshu Publisher")
        print("   工具数量: 5")
        print("   传输协议: Server-Sent Events (SSE)")
        mcp.run(transport="sse")
    else:
        mcp.run()