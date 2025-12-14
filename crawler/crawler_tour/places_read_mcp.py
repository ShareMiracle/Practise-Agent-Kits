#!/usr/bin/env python3
"""
精简版 Tour Places MCP 服务器
只包含景点数据读取功能
"""

import sys
import os
import json
import traceback
from typing import List, Dict, Any

# 设置环境变量确保输出
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

# 调试信息
print(f"🚀 启动精简版 Tour Places MCP 服务器", file=sys.stderr)
print(f"Python版本: {sys.version}", file=sys.stderr)
print(f"工作目录: {os.getcwd()}", file=sys.stderr)
sys.stderr.flush()

# 尝试导入MCP
try:
    # 尝试多种导入方式
    try:
        from mcp.server.fastmcp import FastMCP
        print("✅ 使用标准FastMCP导入", file=sys.stderr)
    except ImportError:
        try:
            import mcp
            from mcp.server.fastmcp import FastMCP
            print("✅ 使用备用MCP导入", file=sys.stderr)
        except ImportError as e:
            print(f"❌ 无法导入MCP: {e}", file=sys.stderr)
            print("请安装: pip install mcp", file=sys.stderr)
            sys.exit(1)
    
    print("✅ MCP导入成功", file=sys.stderr)
    
except Exception as e:
    print(f"❌ 导入错误: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# 创建MCP实例
try:
    mcp = FastMCP("Tour Places Read")
    print("✅ MCP实例创建成功", file=sys.stderr)
except Exception as e:
    print(f"❌ 创建MCP实例失败: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# 配置信息
DATA_ROOT = "./data"   # JSON 数据根目录
print(f"📁 数据目录: {DATA_ROOT}", file=sys.stderr)
print(f"📁 数据目录绝对路径: {os.path.abspath(DATA_ROOT)}", file=sys.stderr)
print(f"📁 数据目录是否存在: {os.path.exists(DATA_ROOT)}", file=sys.stderr)
sys.stderr.flush()

def load_json_files_in_path(path: str) -> List[Dict[str, Any]]:
    """读取一个目录下所有 JSON 文件"""
    items = []
    
    print(f"[DEBUG] 尝试读取路径: {path}", file=sys.stderr)
    print(f"[DEBUG] 绝对路径: {os.path.abspath(path)}", file=sys.stderr)
    print(f"[DEBUG] 路径是否存在: {os.path.exists(path)}", file=sys.stderr)
    
    if not os.path.exists(path):
        print(f"[WARN] 路径不存在: {path}", file=sys.stderr)
        return items
    
    try:
        for root, dirs, files in os.walk(path):
            print(f"[DEBUG] 扫描目录: {root}", file=sys.stderr)
            print(f"[DEBUG] 找到文件: {files}", file=sys.stderr)
            
            for f in files:
                if f.lower().endswith(".json"):
                    fp = os.path.join(root, f)
                    print(f"[DEBUG] 处理文件: {fp}", file=sys.stderr)
                    try:
                        with open(fp, "r", encoding="utf-8") as fh:
                            data = json.load(fh)
                            items.append(data)
                        print(f"[DEBUG] 成功加载: {fp}", file=sys.stderr)
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] JSON解析错误 {fp}: {e}", file=sys.stderr)
                    except Exception as e:
                        print(f"[ERROR] 文件读取错误 {fp}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] 遍历目录时出错: {e}", file=sys.stderr)
    
    print(f"[DEBUG] 总共加载 {len(items)} 个JSON文件", file=sys.stderr)
    sys.stderr.flush()
    return items

@mcp.tool(
    name='get_spots_by_province',
    description='根据省份名称获取该省所有景点数据（从本地JSON文件读取）'
)
def get_spots_by_province(province: str) -> Dict[str, Any]:
    """获取省份景点数据"""
    print(f"🔍 调用 get_spots_by_province: {province}", file=sys.stderr)
    sys.stderr.flush()
    
    # 确保数据目录存在
    if not os.path.exists(DATA_ROOT):
        os.makedirs(DATA_ROOT, exist_ok=True)
        print(f"📁 创建数据根目录: {DATA_ROOT}", file=sys.stderr)
    
    target_path = os.path.join(DATA_ROOT, province)
    print(f"📁 目标路径: {target_path}", file=sys.stderr)
    
    # 如果省份目录不存在，创建示例数据
    if not os.path.exists(target_path):
        os.makedirs(target_path, exist_ok=True)
        print(f"📁 创建省份目录: {target_path}", file=sys.stderr)
        
        # 创建示例JSON文件
        example_file = os.path.join(target_path, "示例景点.json")
        with open(example_file, "w", encoding="utf-8") as f:
            json.dump({
                "name": f"{province}示例景点",
                "province": province,
                "city": "示例城市",
                "description": f"这是{province}的一个示例景点，请添加实际数据",
                "rating": 4.5,
                "address": f"{province}某地",
                "tags": ["示例", "景点"],
                "recommended_hours": 2
            }, f, ensure_ascii=False, indent=2)
        
        print(f"📄 创建示例文件: {example_file}", file=sys.stderr)
    
    result = load_json_files_in_path(target_path)
    
    return {
        "province": province,
        "spots": result,
        "count": len(result),
        "path_used": target_path
    }

@mcp.tool(
    name='get_spots_by_city',
    description='根据省份和城市名称获取景点数据（从本地JSON文件读取）'
)
def get_spots_by_city(province: str, city: str) -> Dict[str, Any]:
    """获取城市景点数据"""
    print(f"🔍 调用 get_spots_by_city: {province}/{city}", file=sys.stderr)
    sys.stderr.flush()
    
    # 确保数据目录存在
    if not os.path.exists(DATA_ROOT):
        os.makedirs(DATA_ROOT, exist_ok=True)
        print(f"📁 创建数据根目录: {DATA_ROOT}", file=sys.stderr)
    
    # 确保省份目录存在
    province_path = os.path.join(DATA_ROOT, province)
    if not os.path.exists(province_path):
        os.makedirs(province_path, exist_ok=True)
        print(f"📁 创建省份目录: {province_path}", file=sys.stderr)
    
    target_path = os.path.join(DATA_ROOT, province, city)
    print(f"📁 目标路径: {target_path}", file=sys.stderr)
    
    # 如果城市目录不存在，创建示例数据
    if not os.path.exists(target_path):
        os.makedirs(target_path, exist_ok=True)
        print(f"📁 创建城市目录: {target_path}", file=sys.stderr)
        
        # 创建示例JSON文件
        example_file = os.path.join(target_path, f"{city}示例景点.json")
        with open(example_file, "w", encoding="utf-8") as f:
            json.dump({
                "name": f"{city}示例景点",
                "province": province,
                "city": city,
                "description": f"这是{city}的一个示例景点，请添加实际数据",
                "rating": 4.5,
                "address": f"{city}某地",
                "tags": ["示例", "景点"],
                "recommended_hours": 2
            }, f, ensure_ascii=False, indent=2)
        
        print(f"📄 创建示例文件: {example_file}", file=sys.stderr)
    
    result = load_json_files_in_path(target_path)
    
    return {
        "province": province,
        "city": city,
        "spots": result,
        "count": len(result),
        "path_used": target_path
    }

@mcp.tool(
    name='get_all_provinces',
    description='获取所有有数据的省份列表'
)
def get_all_provinces() -> Dict[str, Any]:
    """获取所有省份列表"""
    print(f"🔍 调用 get_all_provinces", file=sys.stderr)
    sys.stderr.flush()
    
    if not os.path.exists(DATA_ROOT):
        return {
            "success": False,
            "message": f"数据目录不存在: {DATA_ROOT}",
            "provinces": []
        }
    
    provinces = []
    try:
        for item in os.listdir(DATA_ROOT):
            item_path = os.path.join(DATA_ROOT, item)
            if os.path.isdir(item_path):
                provinces.append(item)
        
        print(f"[DEBUG] 找到 {len(provinces)} 个省份", file=sys.stderr)
        
    except Exception as e:
        print(f"[ERROR] 获取省份列表失败: {e}", file=sys.stderr)
    
    return {
        "success": True,
        "data_root": DATA_ROOT,
        "provinces": sorted(provinces),
        "count": len(provinces)
    }

@mcp.tool(
    name='get_cities_in_province',
    description='获取指定省份下的所有城市列表'
)
def get_cities_in_province(province: str) -> Dict[str, Any]:
    """获取省份下的城市列表"""
    print(f"🔍 调用 get_cities_in_province: {province}", file=sys.stderr)
    sys.stderr.flush()
    
    target_path = os.path.join(DATA_ROOT, province)
    
    if not os.path.exists(target_path):
        return {
            "success": False,
            "message": f"省份目录不存在: {province}",
            "province": province,
            "cities": []
        }
    
    cities = []
    try:
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            if os.path.isdir(item_path):
                cities.append(item)
        
        print(f"[DEBUG] 在 {province} 找到 {len(cities)} 个城市", file=sys.stderr)
        
    except Exception as e:
        print(f"[ERROR] 获取城市列表失败: {e}", file=sys.stderr)
    
    return {
        "success": True,
        "province": province,
        "cities": sorted(cities),
        "count": len(cities)
    }

@mcp.tool(
    name='search_spots_by_keyword',
    description='根据关键词搜索景点'
)
def search_spots_by_keyword(keyword: str, max_results: int = 20) -> Dict[str, Any]:
    """根据关键词搜索景点"""
    print(f"🔍 调用 search_spots_by_keyword: {keyword}", file=sys.stderr)
    sys.stderr.flush()
    
    if not os.path.exists(DATA_ROOT):
        return {
            "success": False,
            "message": f"数据目录不存在: {DATA_ROOT}",
            "keyword": keyword,
            "spots": []
        }
    
    results = []
    try:
        # 遍历所有省份
        for province in os.listdir(DATA_ROOT):
            province_path = os.path.join(DATA_ROOT, province)
            if not os.path.isdir(province_path):
                continue
            
            # 遍历省份下的城市
            for city in os.listdir(province_path):
                city_path = os.path.join(province_path, city)
                if not os.path.isdir(city_path):
                    continue
                
                # 加载城市的所有景点
                spots = load_json_files_in_path(city_path)
                
                # 过滤包含关键词的景点
                for spot in spots:
                    spot_name = spot.get("name", "")
                    spot_desc = spot.get("description", "")
                    spot_tags = spot.get("tags", [])
                    
                    # 检查关键词是否出现在名称、描述或标签中
                    if (keyword.lower() in str(spot_name).lower() or 
                        keyword.lower() in str(spot_desc).lower() or
                        any(keyword.lower() in str(tag).lower() for tag in spot_tags)):
                        
                        # 添加省份和城市信息
                        spot_copy = spot.copy()
                        spot_copy["province"] = province
                        spot_copy["city"] = city
                        results.append(spot_copy)
                        
                        if len(results) >= max_results:
                            break
                
                if len(results) >= max_results:
                    break
            
            if len(results) >= max_results:
                break
        
        print(f"[DEBUG] 找到 {len(results)} 个匹配结果", file=sys.stderr)
        
    except Exception as e:
        print(f"[ERROR] 搜索失败: {e}", file=sys.stderr)
    
    return {
        "success": True,
        "keyword": keyword,
        "spots": results,
        "count": len(results)
    }

# 主函数
if __name__ == "__main__":
    try:
        print("=" * 60, file=sys.stderr)
        print("🚀 精简版 Tour Places MCP 服务器已启动", file=sys.stderr)
        print("📁 数据目录:", os.path.abspath(DATA_ROOT), file=sys.stderr)
        print("📁 数据目录存在:", os.path.exists(DATA_ROOT), file=sys.stderr)
        print("🛠️ 可用工具:", file=sys.stderr)
        print("   1. get_spots_by_province - 省份景点查询", file=sys.stderr)
        print("   2. get_spots_by_city - 城市景点查询", file=sys.stderr)
        print("   3. get_all_provinces - 获取所有省份", file=sys.stderr)
        print("   4. get_cities_in_province - 获取省份城市", file=sys.stderr)
        print("   5. search_spots_by_keyword - 关键词搜索景点", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.stderr.flush()
        
        # 运行MCP服务器
        mcp.run()
        
    except KeyboardInterrupt:
        print("\n👋 服务器被用户中断", file=sys.stderr)
    except Exception as e:
        print(f"💥 服务器运行错误: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # 等待以便查看错误
        input("按Enter键退出...")