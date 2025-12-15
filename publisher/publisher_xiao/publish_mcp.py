from mcp.server.fastmcp import FastMCP
import os
from typing import List, Dict, Any

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


if __name__ == "__main__":
    import sys
    
    if "--sse" in sys.argv or os.getenv("MCP_TRANSPORT") == "sse":
        print("🚀 启动 Xiaohongshu Publisher MCP 服务器 (SSE模式)")
        print("   服务名称: Xiaohongshu Publisher")
        print("   工具数量: 2")
        print("   传输协议: Server-Sent Events (SSE)")
        mcp.run(transport="sse")
    else:
        mcp.run()