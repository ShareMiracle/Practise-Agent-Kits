"""
基于高德地图API的路径规划MCP
支持驾车、步行、骑行、电动车、公交五种出行方式
使用FastMCP封装
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional
import httpx
from mcp import types
from mcp.types import Tool, TextContent
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from enum import Enum
import math

# 配置
AMAP_BASE_URL = "https://restapi.amap.com"
AMAP_API_KEY = os.environ.get("AMAP_API_KEY", "")

if not AMAP_API_KEY:
    print("请设置环境变量 AMAP_API_KEY", file=sys.stderr)
    sys.exit(1)

# 路径规划类型枚举
class RouteType(str, Enum):
    DRIVING = "driving"
    WALKING = "walking"
    BICYCLING = "bicycling"
    ELECTROBIKE = "electrobike"
    TRANSIT = "transit"

# 驾车策略枚举
class DrivingStrategy(str, Enum):
    DEFAULT = "0"
    AVOID_CONGESTION = "1"
    HIGHWAY_FIRST = "2"
    NO_HIGHWAY = "3"
    LESS_COST = "4"
    MAIN_ROAD_FIRST = "5"
    FASTEST = "6"

# 输入模型
class RoutePlanningRequest(BaseModel):
    """路径规划请求参数"""
    route_type: RouteType = Field(
        default=RouteType.DRIVING,
        description="路径规划类型: driving(驾车), walking(步行), bicycling(骑行), electrobike(电动车), transit(公交)"
    )
    origin: str = Field(
        description="起点，可以是: 1) 经纬度坐标(格式: 经度,纬度) 2) 地名/地址 3) POI名称"
    )
    destination: str = Field(
        description="终点，可以是: 1) 经纬度坐标(格式: 经度,纬度) 2) 地名/地址 3) POI名称"
    )
    waypoints: Optional[List[str]] = Field(
        default=None,
        description="途经点列表，仅驾车支持。格式同起点终点"
    )
    city: Optional[str] = Field(
        default=None,
        description="城市名称(用于地址解析)，如'北京市'。如果不提供，会自动从地址中解析或使用全国范围"
    )
    strategy: Optional[str] = Field(
        default=None,
        description=f"路径策略。驾车时可选: {', '.join([f'{e.name}={e.value}' for e in DrivingStrategy])}"
    )
    alternative_routes: Optional[int] = Field(
        default=1,
        description="备选路线数量(1-3)，步行/骑行/电动车有效"
    )
    departure_time: Optional[str] = Field(
        default=None,
        description="出发时间(公交专用)，格式: 2024-01-01 08:00"
    )

class LocationInfo(BaseModel):
    """位置信息"""
    name: str
    location: Optional[str] = None  # 经度,纬度
    address: Optional[str] = None
    city: Optional[str] = None
    adcode: Optional[str] = None
    formatted_address: Optional[str] = None

class RouteStep(BaseModel):
    """路径步骤"""
    instruction: str
    road_name: Optional[str] = None
    distance: float  # 米
    duration: float  # 秒
    polyline: Optional[str] = None
    action: Optional[str] = None
    assistant_action: Optional[str] = None

class RoutePlan(BaseModel):
    """路径规划结果"""
    route_type: str
    origin: LocationInfo
    destination: LocationInfo
    waypoints: List[LocationInfo] = []
    total_distance: float  # 米
    total_duration: float  # 秒
    total_taxi_fare: Optional[float] = None  # 出租车费用，元
    total_tolls: Optional[float] = None  # 过路费，元
    traffic_lights: Optional[int] = None  # 红绿灯数量
    steps: List[RouteStep] = []
    polyline: Optional[str] = None
    restrictions: Optional[bool] = None  # 是否有限行路段
    alternative_plans: List["RoutePlan"] = []  # 备选方案
    
    def to_text_summary(self) -> str:
        """转换为文本摘要"""
        # 计算总时间（小时、分钟、秒）
        total_seconds = int(self.total_duration)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        distance_km = self.total_distance / 1000
        
        summary = [
            f"🚗 路径规划结果 ({self.route_type})",
            f"起点: {self.origin.formatted_address or self.origin.name or self.origin.address}",
            f"终点: {self.destination.formatted_address or self.destination.name or self.destination.address}",
            f"总距离: {distance_km:.1f}公里"
        ]
        
        # 时间显示逻辑
        if hours > 0:
            if minutes > 0:
                summary.append(f"预计时间: {hours}小时{minutes}分钟")
            else:
                summary.append(f"预计时间: {hours}小时")
        elif minutes > 0:
            summary.append(f"预计时间: {minutes}分钟")
        elif seconds > 0:
            summary.append(f"预计时间: {seconds}秒")
        else:
            # 如果时间为0，根据距离估算
            if distance_km > 0:
                if self.route_type == "公交":
                    # 公交平均速度15km/h
                    estimated_hours = distance_km / 15
                    if estimated_hours >= 1:
                        hours = int(estimated_hours)
                        minutes = int((estimated_hours - hours) * 60)
                        summary.append(f"预计时间: 约{hours}小时{minutes}分钟")
                    else:
                        minutes = int(estimated_hours * 60)
                        summary.append(f"预计时间: 约{minutes}分钟")
                elif self.route_type == "驾车":
                    # 驾车平均速度30km/h
                    estimated_hours = distance_km / 30
                    if estimated_hours >= 1:
                        hours = int(estimated_hours)
                        minutes = int((estimated_hours - hours) * 60)
                        summary.append(f"预计时间: 约{hours}小时{minutes}分钟")
                    else:
                        minutes = int(estimated_hours * 60)
                        summary.append(f"预计时间: 约{minutes}分钟")
                elif self.route_type == "骑行":
                    # 骑行平均速度15km/h
                    estimated_hours = distance_km / 15
                    if estimated_hours >= 1:
                        hours = int(estimated_hours)
                        minutes = int((estimated_hours - hours) * 60)
                        summary.append(f"预计时间: 约{hours}小时{minutes}分钟")
                    else:
                        minutes = int(estimated_hours * 60)
                        summary.append(f"预计时间: 约{minutes}分钟")
                elif self.route_type == "步行":
                    # 步行平均速度5km/h
                    estimated_hours = distance_km / 5
                    if estimated_hours >= 1:
                        hours = int(estimated_hours)
                        minutes = int((estimated_hours - hours) * 60)
                        summary.append(f"预计时间: 约{hours}小时{minutes}分钟")
                    else:
                        minutes = int(estimated_hours * 60)
                        summary.append(f"预计时间: 约{minutes}分钟")
            else:
                summary.append("预计时间: 未知")
        
        if self.total_taxi_fare:
            if self.route_type == "公交":
                summary.append(f"公交费用: {self.total_taxi_fare:.2f}元")
            else:
                summary.append(f"出租车费用: {self.total_taxi_fare:.2f}元")
        
        if self.total_tolls:
            summary.append(f"过路费: {self.total_tolls:.2f}元")
        
        if self.traffic_lights:
            summary.append(f"红绿灯数量: {self.traffic_lights}个")
        
        if self.restrictions is not None:
            summary.append(f"限行路段: {'是' if self.restrictions else '否'}")
        
        if self.steps:
            summary.append("\n详细路线:")
            for i, step in enumerate(self.steps):
                # 构建步骤描述
                step_desc = step.instruction
                
                # 如果有道路名称，添加到描述中
                if step.road_name and step.road_name.strip():
                    step_desc = f"沿{step.road_name}{step.instruction}"
                
                # 显示步骤距离和时间
                if step.distance > 0:
                    step_desc += f" ({step.distance:.0f}米"
                    if step.duration > 0:
                        # 转换秒为分钟
                        step_minutes = step.duration / 60
                        step_desc += f"，约{step_minutes:.0f}分钟"
                    step_desc += ")"
                
                summary.append(f"{i+1}. {step_desc}")
        
        if self.alternative_plans:
            summary.append(f"\n🔄 共有{len(self.alternative_plans)}个备选方案")
        
        return "\n".join(summary)

class RoutePlanningMCP:
    """路径规划MCP服务"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def geocode(self, address: str, city: Optional[str] = None) -> Optional[LocationInfo]:
        """地理编码：将地址转换为坐标"""
        try:
            params = {
                "key": AMAP_API_KEY,
                "address": address,
                "output": "json"
            }
            if city:
                params["city"] = city
                
            response = await self.client.get(f"{AMAP_BASE_URL}/v3/geocode/geo", params=params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("geocodes"):
                geo = data["geocodes"][0]
                return LocationInfo(
                    name=address,
                    location=geo.get("location"),
                    formatted_address=geo.get("formatted_address") or geo.get("address", address),
                    city=geo.get("city"),
                    adcode=geo.get("adcode"),
                    address=geo.get("address", address)
                )
            else:
                print(f"地理编码返回状态错误: {data.get('status')}, 信息: {data.get('info')}", file=sys.stderr)
        except Exception as e:
            print(f"地理编码错误 {address}: {e}", file=sys.stderr)
        
        return None
    
    def parse_location(self, location_str: str) -> Optional[str]:
        """解析位置字符串，返回经纬度字符串"""
        # 如果已经是坐标格式
        location_str = location_str.strip()
        if "," in location_str and len(location_str.split(",")) == 2:
            try:
                parts = location_str.split(",")
                lon = float(parts[0].strip())
                lat = float(parts[1].strip())
                if -180 <= lon <= 180 and -90 <= lat <= 90:
                    return f"{lon},{lat}"
            except (ValueError, IndexError):
                pass
        return None
    
    async def get_coordinates(self, location: str, city: Optional[str] = None) -> Optional[str]:
        """获取坐标，支持多种输入格式"""
        # 检查是否已经是坐标
        coords = self.parse_location(location)
        if coords:
            return coords
        
        # 尝试地理编码
        location_info = await self.geocode(location, city)
        if location_info and location_info.location:
            return location_info.location
        
        # 尝试搜索POI
        try:
            params = {
                "key": AMAP_API_KEY,
                "keywords": location,
                "output": "json",
                "offset": "1"
            }
            if city:
                params["city"] = city
                
            response = await self.client.get(f"{AMAP_BASE_URL}/v3/place/text", params=params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("pois"):
                poi = data["pois"][0]
                if poi.get("location"):
                    return poi["location"]
        except Exception as e:
            print(f"POI搜索错误 {location}: {e}", file=sys.stderr)
        
        print(f"警告: 无法解析位置 '{location}'", file=sys.stderr)
        return None
    
    async def get_location_info(self, location: str, city: Optional[str] = None) -> LocationInfo:
        """获取位置信息"""
        # 先尝试地理编码
        location_info = await self.geocode(location, city)
        if location_info:
            return location_info
        
        # 如果地理编码失败，尝试搜索POI
        try:
            params = {
                "key": AMAP_API_KEY,
                "keywords": location,
                "output": "json",
                "offset": "1"
            }
            if city:
                params["city"] = city
                
            response = await self.client.get(f"{AMAP_BASE_URL}/v3/place/text", params=params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("pois"):
                poi = data["pois"][0]
                return LocationInfo(
                    name=poi.get("name", location),
                    location=poi.get("location"),
                    address=poi.get("address"),
                    city=poi.get("cityname"),
                    adcode=poi.get("adcode"),
                    formatted_address=poi.get("address", location)
                )
        except Exception as e:
            print(f"获取位置信息错误 {location}: {e}", file=sys.stderr)
        
        # 如果都失败，返回基本信息
        return LocationInfo(name=location)
    
    async def plan_driving_route(
        self, 
        origin: str, 
        destination: str, 
        waypoints: Optional[List[str]] = None,
        strategy: Optional[str] = None,
        city: Optional[str] = None
    ) -> List[RoutePlan]:
        """规划驾车路线"""
        origin_coords = await self.get_coordinates(origin, city)
        dest_coords = await self.get_coordinates(destination, city)
        
        if not origin_coords:
            raise ValueError(f"无法解析起点坐标: {origin}")
        if not dest_coords:
            raise ValueError(f"无法解析终点坐标: {destination}")
        
        print(f"调试: 起点坐标: {origin_coords}, 终点坐标: {dest_coords}", file=sys.stderr)
        
        # 获取位置详细信息
        origin_info = await self.get_location_info(origin, city)
        dest_info = await self.get_location_info(destination, city)
        
        params = {
            "key": AMAP_API_KEY,
            "origin": origin_coords,
            "destination": dest_coords,
            "output": "json",
            "extensions": "all",
            "show_fields": "cost,tmcs"
        }
        
        waypoint_infos = []
        
        if waypoints:
            waypoint_coords = []
            for wp in waypoints:
                wp_coords = await self.get_coordinates(wp, city)
                if wp_coords:
                    waypoint_coords.append(wp_coords)
                    waypoint_infos.append(await self.get_location_info(wp, city))
            if waypoint_coords:
                params["waypoints"] = ";".join(waypoint_coords)
        
        if strategy:
            params["strategy"] = strategy
        
        try:
            response = await self.client.get(f"{AMAP_BASE_URL}/v5/direction/driving", params=params)
            data = response.json()
            
            print(f"调试: API响应状态: {data.get('status')}, 信息: {data.get('info')}", file=sys.stderr)
            
            if data.get("status") != "1":
                error_msg = data.get("info", "未知错误")
                raise Exception(f"API错误: {error_msg}")
            
            plans = []
            route_data = data.get("route", {})
            paths = route_data.get("paths", [])
            
            print(f"调试: 找到 {len(paths)} 条路径", file=sys.stderr)
            
            for path_idx, path in enumerate(paths):
                # 尝试不同字段名获取距离和时间
                distance = 0
                if "distance" in path:
                    try:
                        distance = float(path.get("distance", 0))
                    except (ValueError, TypeError):
                        pass
                
                duration = 0
                # 尝试不同可能的duration字段
                for duration_key in ["duration", "time", "total_time"]:
                    if duration_key in path and path[duration_key]:
                        try:
                            duration = float(path.get(duration_key, 0))
                            break
                        except (ValueError, TypeError):
                            continue
                
                # 如果还是没有获取到duration，根据距离估算
                if duration <= 0 and distance > 0:
                    # 假设平均车速60km/h
                    duration = (distance / 1000) / 60 * 3600  # 转换为秒
                
                taxi_cost = path.get("taxi_cost")
                tolls = path.get("tolls")
                
                # 解析步骤
                steps = []
                step_list = path.get("steps", [])
                print(f"调试: 路径 {path_idx+1} 有 {len(step_list)} 个步骤", file=sys.stderr)
                
                for step_idx, step in enumerate(step_list):
                    instruction = step.get("instruction", "")
                    road_name = step.get("road", "")
                    
                    # 获取步骤距离
                    step_distance = 0
                    if "distance" in step:
                        try:
                            step_distance = float(step.get("distance", 0))
                        except (ValueError, TypeError):
                            pass
                    
                    # 获取步骤时间
                    step_duration = 0
                    for duration_key in ["duration", "time", "step_time"]:
                        if duration_key in step and step[duration_key]:
                            try:
                                step_duration = float(step.get(duration_key, 0))
                                break
                            except (ValueError, TypeError):
                                continue
                    
                    steps.append(RouteStep(
                        instruction=instruction,
                        road_name=road_name,
                        distance=step_distance,
                        duration=step_duration
                    ))
                
                plan = RoutePlan(
                    route_type="驾车",
                    origin=origin_info,
                    destination=dest_info,
                    waypoints=waypoint_infos,
                    total_distance=distance,
                    total_duration=duration,
                    total_taxi_fare=float(taxi_cost) if taxi_cost else None,
                    total_tolls=float(tolls) if tolls else None,
                    steps=steps
                )
                plans.append(plan)
            
            return plans
            
        except Exception as e:
            print(f"API请求错误: {e}", file=sys.stderr)
            raise
    
    async def plan_walking_route(
        self, 
        origin: str, 
        destination: str,
        city: Optional[str] = None
    ) -> List[RoutePlan]:
        """规划步行路线"""
        origin_coords = await self.get_coordinates(origin, city)
        dest_coords = await self.get_coordinates(destination, city)
        
        if not origin_coords or not dest_coords:
            raise ValueError("无法解析起点或终点坐标")
        
        origin_info = await self.get_location_info(origin, city)
        dest_info = await self.get_location_info(destination, city)
        
        params = {
            "key": AMAP_API_KEY,
            "origin": origin_coords,
            "destination": dest_coords,
            "output": "json"
        }
        
        response = await self.client.get(f"{AMAP_BASE_URL}/v5/direction/walking", params=params)
        data = response.json()
        
        if data.get("status") != "1":
            error_msg = data.get("info", "未知错误")
            raise Exception(f"API错误: {error_msg}")
        
        plans = []
        route_data = data.get("route", {})
        paths = route_data.get("paths", [])
        
        for path in paths:
            distance = float(path.get("distance", 0))
            duration = float(path.get("duration", 0))
            
            # 如果API返回的时间为0，根据距离估算（步行速度5km/h）
            if duration <= 0 and distance > 0:
                duration = (distance / 1000) / 5 * 3600
            
            # 解析步骤
            steps = []
            for step in path.get("steps", []):
                instruction = step.get("instruction", "")
                step_distance = float(step.get("distance", 0))
                step_duration = float(step.get("duration", 0))
                
                steps.append(RouteStep(
                    instruction=instruction,
                    distance=step_distance,
                    duration=step_duration
                ))
            
            plan = RoutePlan(
                route_type="步行",
                origin=origin_info,
                destination=dest_info,
                total_distance=distance,
                total_duration=duration,
                steps=steps
            )
            plans.append(plan)
        
        return plans
    
    async def plan_cycling_route(
        self, 
        origin: str, 
        destination: str,
        city: Optional[str] = None
    ) -> List[RoutePlan]:
        """规划骑行路线（包括自行车和电动车）"""
        origin_coords = await self.get_coordinates(origin, city)
        dest_coords = await self.get_coordinates(destination, city)
        
        if not origin_coords or not dest_coords:
            raise ValueError("无法解析起点或终点坐标")
        
        origin_info = await self.get_location_info(origin, city)
        dest_info = await self.get_location_info(destination, city)
        
        # 使用骑行API
        params = {
            "key": AMAP_API_KEY,
            "origin": origin_coords,
            "destination": dest_coords,
            "output": "json"
        }
        
        response = await self.client.get(f"{AMAP_BASE_URL}/v5/direction/bicycling", params=params)
        data = response.json()
        
        if data.get("status") != "1":
            error_msg = data.get("info", "未知错误")
            raise Exception(f"API错误: {error_msg}")
        
        plans = []
        route_data = data.get("route", {})
        paths = route_data.get("paths", [])
        
        for path in paths:
            distance = float(path.get("distance", 0))
            duration = float(path.get("duration", 0))
            
            # 如果API返回的时间为0，根据距离估算（骑行速度15km/h）
            if duration <= 0 and distance > 0:
                duration = (distance / 1000) / 15 * 3600
            
            # 解析步骤
            steps = []
            for step in path.get("steps", []):
                instruction = step.get("instruction", "")
                step_distance = float(step.get("distance", 0))
                step_duration = float(step.get("duration", 0))
                
                steps.append(RouteStep(
                    instruction=instruction,
                    distance=step_distance,
                    duration=step_duration
                ))
            
            plan = RoutePlan(
                route_type="骑行",
                origin=origin_info,
                destination=dest_info,
                total_distance=distance,
                total_duration=duration,
                steps=steps
            )
            plans.append(plan)
        
        return plans
    
    async def plan_transit_route(
        self, 
        origin: str, 
        destination: str,
        city: Optional[str] = None
    ) -> List[RoutePlan]:
        """规划公交路线"""
        try:
            origin_coords = await self.get_coordinates(origin, city)
            dest_coords = await self.get_coordinates(destination, city)
            
            if not origin_coords:
                raise ValueError(f"无法解析起点坐标: {origin}")
            if not dest_coords:
                raise ValueError(f"无法解析终点坐标: {destination}")
            
            # 获取位置详细信息
            origin_info = await self.get_location_info(origin, city)
            dest_info = await self.get_location_info(destination, city)
            
            # 构建参数 - 使用v5接口的正确参数
            params = {
                "key": AMAP_API_KEY,
                "origin": origin_coords,
                "destination": dest_coords,
                "output": "json",
                "extensions": "all"
            }
            
            # 尝试获取城市编码（citycode）
            city_code = None
            if city:
                # 使用地理编码获取城市编码
                try:
                    geo_params = {
                        "key": AMAP_API_KEY,
                        "address": city,
                        "output": "json"
                    }
                    response = await self.client.get(f"{AMAP_BASE_URL}/v3/geocode/geo", params=geo_params)
                    geo_data = response.json()
                    
                    if geo_data.get("status") == "1" and geo_data.get("geocodes"):
                        geo = geo_data["geocodes"][0]
                        city_code = geo.get("citycode")
                        if not city_code and geo.get("adcode"):
                            # 如果没有citycode，使用adcode（通常是相同的）
                            city_code = geo.get("adcode")
                except Exception as e:
                    print(f"获取城市编码错误: {e}", file=sys.stderr)
            
            # 设置城市参数（使用citycode格式）
            if city_code:
                params["city1"] = city_code  # 起点城市编码
                params["city2"] = city_code  # 终点城市编码，假设同城
            else:
                # 如果没有获取到城市编码，但用户提供了城市名，尝试使用adcode
                if city and origin_info.adcode:
                    params["city1"] = origin_info.adcode
                    params["city2"] = origin_info.adcode
                elif origin_info.city:
                    # 尝试从城市名获取adcode
                    try:
                        # 调用行政区划查询接口
                        district_params = {
                            "key": AMAP_API_KEY,
                            "keywords": origin_info.city,
                            "subdistrict": "0",  # 不返回下级行政区
                            "output": "json"
                        }
                        response = await self.client.get(f"{AMAP_BASE_URL}/v3/config/district", params=district_params)
                        district_data = response.json()
                        
                        if district_data.get("status") == "1" and district_data.get("districts"):
                            adcode = district_data["districts"][0].get("adcode")
                            if adcode:
                                params["city1"] = adcode
                                params["city2"] = adcode
                    except Exception as e:
                        print(f"查询行政区划错误: {e}", file=sys.stderr)
            
            print(f"调试: 公交规划参数: {params}", file=sys.stderr)
            
            # 使用正确的v5接口
            url = f"{AMAP_BASE_URL}/v5/direction/transit/integrated"
            print(f"调试: 请求URL: {url}", file=sys.stderr)
            
            response = await self.client.get(url, params=params)
            data = response.json()
            
            print(f"调试: 公交API响应: {data}", file=sys.stderr)
            
            if data.get("status") != "1":
                error_msg = data.get("info", "未知错误")
                if error_msg == "MISSING_REQUIRED_PARAMS":
                    # 可能是城市参数问题，尝试不带城市参数
                    print("调试: 尝试不带城市参数...", file=sys.stderr)
                    params.pop("city1", None)
                    params.pop("city2", None)
                    response = await self.client.get(url, params=params)
                    data = response.json()
                    
                    if data.get("status") != "1":
                        # 尝试使用ad1和ad2参数（行政区划编码）
                        params["ad1"] = origin_info.adcode or ""
                        params["ad2"] = dest_info.adcode or ""
                        response = await self.client.get(url, params=params)
                        data = response.json()
                        
                        if data.get("status") != "1":
                            raise Exception(f"公交路径规划失败: {data.get('info', '未知错误')}")
                
            return self._parse_transit_response_v5(data, origin_info, dest_info)
                
        except Exception as e:
            print(f"公交API请求错误: {e}", file=sys.stderr)
            raise

    def _parse_transit_response_v5(self, data: dict, origin_info: LocationInfo, 
                                dest_info: LocationInfo) -> List[RoutePlan]:
        """解析公交响应数据（v5接口）"""
        plans = []
        
        route_data = data.get("route", {})
        transits = route_data.get("transits", [])
        
        print(f"调试: 找到 {len(transits)} 个公交方案", file=sys.stderr)
        
        for transit_idx, transit in enumerate(transits[:3]):  # 只取前3个方案
            # 获取基本信息
            distance_str = transit.get("distance", "0")
            duration_str = transit.get("duration", "0")
            cost_str = transit.get("cost", "0")
            
            # 转换距离
            try:
                distance = float(distance_str)
            except (ValueError, TypeError):
                print(f"警告: 无法解析距离 '{distance_str}'", file=sys.stderr)
                distance = 0
            
            # 转换时间 - 高德API返回的是字符串格式的时间（秒）
            try:
                duration = float(duration_str)
            except (ValueError, TypeError):
                print(f"警告: 无法解析时间 '{duration_str}'，尝试从segments中计算", file=sys.stderr)
                duration = 0
            
            # 转换费用
            try:
                cost = float(cost_str)
            except (ValueError, TypeError):
                print(f"警告: 无法解析费用 '{cost_str}'", file=sys.stderr)
                cost = 0
            
            print(f"调试: 方案 {transit_idx+1}: 距离={distance}米, 时间={duration}秒, 费用={cost}元", file=sys.stderr)
            
            # 解析步骤
            steps = []
            segments = transit.get("segments", [])
            
            if segments:
                print(f"调试: 有 {len(segments)} 个segments", file=sys.stderr)
            
            segment_total_duration = 0  # 用于从segments中累加时间
            segment_total_distance = 0  # 用于从segments中累加距离
            
            for segment_idx, segment in enumerate(segments):
                print(f"调试: 解析segment {segment_idx+1}: {segment.keys()}", file=sys.stderr)
                
                # 步行段
                if "walking" in segment:
                    walking = segment.get("walking", {})
                    print(f"调试: walking字段类型: {type(walking)}", file=sys.stderr)
                    
                    if walking:
                        if isinstance(walking, dict):
                            walk_distance_str = walking.get("distance", "0")
                            walk_duration_str = walking.get("duration", "0")
                            
                            try:
                                walk_distance = float(walk_distance_str)
                            except (ValueError, TypeError):
                                walk_distance = 0
                            
                            try:
                                walk_duration = float(walk_duration_str)
                            except (ValueError, TypeError):
                                walk_duration = 0
                            
                            # 获取步行导航指令
                            walk_instruction = walking.get("instruction", "")
                            if not walk_instruction and walk_distance > 0:
                                walk_instruction = f"步行{walk_distance:.0f}米"
                            
                            # 获取道路名称
                            walk_road = walking.get("road", "")
                            
                            step = RouteStep(
                                instruction=walk_instruction,
                                road_name=walk_road,
                                distance=walk_distance,
                                duration=walk_duration
                            )
                            steps.append(step)
                            
                            segment_total_duration += walk_duration
                            segment_total_distance += walk_distance
                            
                            print(f"调试: 步行段 - 距离={walk_distance}米, 时间={walk_duration}秒", file=sys.stderr)
                            
                        elif isinstance(walking, str):
                            # 尝试从字符串中提取信息
                            step = RouteStep(
                                instruction="步行一段距离",
                                distance=0,
                                duration=0
                            )
                            steps.append(step)
                
                # 公交/地铁段
                bus_data = segment.get("bus", {})
                if bus_data:
                    print(f"调试: bus_data字段类型: {type(bus_data)}", file=sys.stderr)
                    
                    if isinstance(bus_data, dict):
                        buslines = bus_data.get("buslines", [])
                        print(f"调试: 有 {len(buslines)} 个buslines", file=sys.stderr)
                        
                        for busline in buslines:
                            bus_name = busline.get("name", "公交车")
                            departure = busline.get("departure_stop", {}).get("name", "")
                            arrival = busline.get("arrival_stop", {}).get("name", "")
                            
                            # 获取距离和时间
                            bus_distance_str = busline.get("distance", "0")
                            bus_duration_str = busline.get("duration", "0")
                            
                            try:
                                bus_distance = float(bus_distance_str)
                            except (ValueError, TypeError):
                                bus_distance = 0
                            
                            try:
                                bus_duration = float(bus_duration_str)
                            except (ValueError, TypeError):
                                bus_duration = 0
                            
                            instruction = f"乘坐{bus_name}"
                            if departure and arrival:
                                instruction += f"，从{departure}到{arrival}"
                            
                            # 获取站点数量
                            via_stops = busline.get("via_stops", [])
                            if via_stops:
                                instruction += f"，经过{len(via_stops)}站"
                            
                            step = RouteStep(
                                instruction=instruction,
                                distance=bus_distance,
                                duration=bus_duration
                            )
                            steps.append(step)
                            
                            segment_total_duration += bus_duration
                            segment_total_distance += bus_distance
                            
                            print(f"调试: 公交段 - 距离={bus_distance}米, 时间={bus_duration}秒, 线路={bus_name}", file=sys.stderr)
                
                # 地铁段
                railway_data = segment.get("railway", {})
                if railway_data and isinstance(railway_data, dict):
                    railway_name = railway_data.get("name", "地铁")
                    departure = railway_data.get("departure_stop", {}).get("name", "")
                    arrival = railway_data.get("arrival_stop", {}).get("name", "")
                    
                    # 获取距离和时间
                    railway_distance_str = railway_data.get("distance", "0")
                    railway_duration_str = railway_data.get("duration", "0")
                    
                    try:
                        railway_distance = float(railway_distance_str)
                    except (ValueError, TypeError):
                        railway_distance = 0
                    
                    try:
                        railway_duration = float(railway_duration_str)
                    except (ValueError, TypeError):
                        railway_duration = 0
                    
                    instruction = f"乘坐{railway_name}"
                    if departure and arrival:
                        instruction += f"，从{departure}到{arrival}"
                    
                    # 获取站点数量
                    via_stops = railway_data.get("via_stops", [])
                    if via_stops:
                        instruction += f"，经过{len(via_stops)}站"
                    
                    step = RouteStep(
                        instruction=instruction,
                        distance=railway_distance,
                        duration=railway_duration
                    )
                    steps.append(step)
                    
                    segment_total_duration += railway_duration
                    segment_total_distance += railway_distance
                    
                    print(f"调试: 地铁段 - 距离={railway_distance}米, 时间={railway_duration}秒, 线路={railway_name}", file=sys.stderr)
            
            # 如果transit的总时间为0，但segments有时间，使用segments的总时间
            if duration <= 0 and segment_total_duration > 0:
                duration = segment_total_duration
                print(f"调试: 使用segments累加时间: {duration}秒", file=sys.stderr)
            
            # 如果transit的总距离为0，但segments有距离，使用segments的总距离
            if distance <= 0 and segment_total_distance > 0:
                distance = segment_total_distance
                print(f"调试: 使用segments累加距离: {distance}米", file=sys.stderr)
            
            # 创建计划
            plan = RoutePlan(
                route_type="公交",
                origin=origin_info,
                destination=dest_info,
                total_distance=distance,
                total_duration=duration,
                total_taxi_fare=cost if cost > 0 else None,  # 这里存储公交费用
                steps=steps
            )
            plans.append(plan)
            
            print(f"调试: 公交方案 {transit_idx+1} 完成: 总距离={distance}米, 总时间={duration}秒, 步骤数={len(steps)}", file=sys.stderr)
        
        return plans

# 创建FastMCP应用
mcp = FastMCP("amap-route-planning")

@mcp.tool()
async def route_planning(
    origin: str,
    destination: str,
    route_type: RouteType = RouteType.DRIVING,
    waypoints: Optional[List[str]] = None,
    city: Optional[str] = None,
    strategy: Optional[str] = None,
    alternative_routes: int = 1
) -> str:
    """
    路径规划工具，支持驾车、步行、骑行、电动车、公交五种出行方式
    
    Args:
        route_type: 出行方式: driving(驾车), walking(步行), bicycling(骑行), electrobike(电动车), transit(公交)
        origin: 起点，可以是坐标(经度,纬度)、地名、地址或POI名称
        destination: 终点，可以是坐标(经度,纬度)、地名、地址或POI名称
        waypoints: 途经点列表(仅驾车支持)
        city: 城市名称，用于地址解析，如'北京市'
        strategy: 驾车策略: 0(推荐), 1(躲避拥堵), 2(高速优先), 3(不走高速), 4(少收费), 5(大路优先), 6(速度最快)
        alternative_routes: 备选路线数量(1-3)
    """
    try:
        print(f"调试: 开始路径规划 - 类型: {route_type}, 起点: {origin}, 终点: {destination}", file=sys.stderr)
        
        planner = RoutePlanningMCP()
        
        if route_type == RouteType.DRIVING:
            plans = await planner.plan_driving_route(
                origin, destination, waypoints, strategy, city
            )
        elif route_type == RouteType.WALKING:
            plans = await planner.plan_walking_route(origin, destination, city)
        elif route_type in [RouteType.BICYCLING, RouteType.ELECTROBIKE]:
            plans = await planner.plan_cycling_route(origin, destination, city)
        elif route_type == RouteType.TRANSIT:
            plans = await planner.plan_transit_route(origin, destination, city)
        else:
            return f"不支持的路径类型: {route_type}"
        
        if not plans:
            return "未找到合适的路径"
        
        # 格式化输出
        result = []
        for i, plan in enumerate(plans[:alternative_routes]):
            if i > 0:
                result.append(f"\n{'='*50}\n备选方案 {i+1}:")
            result.append(plan.to_text_summary())
        
        return "\n".join(result)
        
    except Exception as e:
        print(f"路径规划异常: {e}", file=sys.stderr)
        return f"路径规划失败: {str(e)}"

@mcp.tool()
async def search_places(
    query: str,
    city: Optional[str] = None,
    limit: int = 5
) -> str:
    """
    搜索地点，支持地名、地址、POI名称
    
    Args:
        query: 搜索关键词，如'天安门'、'苏州博物馆'等
        city: 城市名称，限定搜索范围，如'苏州市'
        limit: 返回结果数量
    """
    try:
        planner = RoutePlanningMCP()
        
        # 先尝试地理编码
        location_info = await planner.geocode(query, city)
        if location_info:
            return f"📍 找到地点: {location_info.formatted_address or location_info.name}\n坐标: {location_info.location}"
        
        # 搜索POI
        params = {
            "key": AMAP_API_KEY,
            "keywords": query,
            "output": "json",
            "offset": str(limit)
        }
        if city:
            params["city"] = city
            
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AMAP_BASE_URL}/v3/place/text", params=params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("pois"):
                pois = data["pois"][:limit]
                result = [f"🔍 搜索 '{query}' 结果:"]
                for i, poi in enumerate(pois, 1):
                    address = poi.get('address', '无地址')
                    if not address or address == "[]":
                        address = "无地址"
                    result.append(f"{i}. {poi['name']} ({address})")
                    if poi.get("location"):
                        result.append(f"   坐标: {poi['location']}")
                return "\n".join(result)
            else:
                return f"未找到与 '{query}' 相关的地点"
                
    except Exception as e:
        return f"搜索失败: {str(e)}"

@mcp.tool()
async def multi_point_route(
    locations: List[str],
    route_type: RouteType = RouteType.DRIVING,
    city: Optional[str] = None
) -> str:
    """
    多点路径规划，按顺序连接多个地点
    
    Args:
        locations: 地点列表，按顺序连接
        route_type: 出行方式
        city: 城市名称，用于地址解析
    """
    if len(locations) < 2:
        return "需要至少2个地点进行多点路径规划"
    
    try:
        planner = RoutePlanningMCP()
        all_plans = []
        
        # 依次规划每对地点之间的路径
        for i in range(len(locations) - 1):
            origin = locations[i]
            destination = locations[i + 1]
            
            if route_type == RouteType.DRIVING:
                plans = await planner.plan_driving_route(origin, destination, city=city)
            elif route_type == RouteType.WALKING:
                plans = await planner.plan_walking_route(origin, destination, city=city)
            elif route_type in [RouteType.BICYCLING, RouteType.ELECTROBIKE]:
                plans = await planner.plan_cycling_route(origin, destination, city=city)
            elif route_type == RouteType.TRANSIT:
                plans = await planner.plan_transit_route(origin, destination, city=city)
            else:
                return f"不支持的路径类型: {route_type}"
            
            if plans:
                all_plans.append((origin, destination, plans[0]))
        
        if not all_plans:
            return "路径规划失败"
        
        # 汇总结果
        result = [f"🚗 多点路径规划 ({route_type})", f"地点顺序: {' → '.join(locations)}", ""]
        
        total_distance = 0
        total_duration = 0
        
        for i, (origin, destination, plan) in enumerate(all_plans, 1):
            result.append(f"第{i}段: {origin} → {destination}")
            result.append(f"  距离: {plan.total_distance/1000:.1f}公里")
            
            hours = int(plan.total_duration // 3600)
            minutes = int((plan.total_duration % 3600) // 60)
            seconds = int(plan.total_duration % 60)
            
            if hours > 0:
                result.append(f"  时间: {hours}小时{minutes}分钟")
            elif minutes > 0:
                result.append(f"  时间: {minutes}分钟")
            else:
                result.append(f"  时间: {seconds}秒")
            
            total_distance += plan.total_distance
            total_duration += plan.total_duration
            result.append("")
        
        result.append("📊 总计:")
        result.append(f"总距离: {total_distance/1000:.1f}公里")
        
        total_hours = int(total_duration // 3600)
        total_minutes = int((total_duration % 3600) // 60)
        total_seconds = int(total_duration % 60)
        
        if total_hours > 0:
            result.append(f"总时间: {total_hours}小时{total_minutes}分钟")
        elif total_minutes > 0:
            result.append(f"总时间: {total_minutes}分钟")
        else:
            result.append(f"总时间: {total_seconds}秒")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"多点路径规划失败: {str(e)}"

# FastMCP会自动处理服务器运行
if __name__ == "__main__":
    mcp.run()