"""
基于高德地图API的天气查询MCP
支持实时天气和未来天气预测
使用FastMCP封装
"""

import os
import sys
from typing import Dict, Any, List, Optional
import httpx
from mcp.types import Tool
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, timedelta
import json

# 配置
AMAP_BASE_URL = "https://restapi.amap.com"
AMAP_API_KEY = os.environ.get("AMAP_API_KEY", "")

if not AMAP_API_KEY:
    print("请设置环境变量 AMAP_API_KEY", file=sys.stderr)
    sys.exit(1)

# 天气类型枚举
class WeatherType(str, Enum):
    BASE = "base"  # 实况天气
    ALL = "all"    # 预报天气

# 天气信息模型
class CurrentWeather(BaseModel):
    """当前天气信息"""
    province: str = Field(description="省份名")
    city: str = Field(description="城市名")
    adcode: str = Field(description="区域编码")
    weather: str = Field(description="天气现象")
    temperature: str = Field(description="实时气温，单位：摄氏度")
    winddirection: str = Field(description="风向描述")
    windpower: str = Field(description="风力级别，单位：级")
    humidity: str = Field(description="空气湿度")
    reporttime: str = Field(description="数据发布的时间")

class ForecastDay(BaseModel):
    """天气预报单日信息"""
    date: str = Field(description="日期")
    week: str = Field(description="星期几")
    dayweather: str = Field(description="白天天气现象")
    nightweather: str = Field(description="晚上天气现象")
    daytemp: str = Field(description="白天温度")
    nighttemp: str = Field(description="晚上温度")
    daywind: str = Field(description="白天风向")
    nightwind: str = Field(description="晚上风向")
    daypower: str = Field(description="白天风力")
    nightpower: str = Field(description="晚上风力")
    
    def to_text(self) -> str:
        """转换为文本格式"""
        return (
            f"{self.date} ({self.week}): "
            f"白天{self.dayweather} {self.daytemp}°C {self.daywind}{self.daypower}，"
            f"夜间{self.nightweather} {self.nighttemp}°C {self.nightwind}{self.nightpower}"
        )

class WeatherForecast(BaseModel):
    """天气预报信息"""
    city: str = Field(description="城市名称")
    adcode: str = Field(description="城市编码")
    province: str = Field(description="省份名称")
    reporttime: str = Field(description="预报发布时间")
    casts: List[ForecastDay] = Field(description="预报数据")

class WeatherResult(BaseModel):
    """天气查询结果"""
    status: str = Field(description="返回状态: 1-成功, 0-失败")
    info: str = Field(description="返回的状态信息")
    infocode: str = Field(description="返回状态说明")
    current: Optional[CurrentWeather] = Field(default=None, description="实况天气数据")
    forecast: Optional[WeatherForecast] = Field(default=None, description="预报天气数据")
    
    def to_text_summary(self, weather_type: str = "base") -> str:
        """转换为文本摘要"""
        if self.status != "1":
            return f"天气查询失败: {self.info}"
        
        result = []
        
        if weather_type == "base" and self.current:
            current = self.current
            result.append(f"🌤️ 当前天气 - {current.city} ({current.reporttime})")
            result.append(f"📍 位置: {current.province}{current.city}")
            result.append(f"🌡️ 温度: {current.temperature}°C")
            result.append(f"☁️ 天气: {current.weather}")
            result.append(f"💨 风向风力: {current.winddirection}{current.windpower}")
            result.append(f"💧 湿度: {current.humidity}%")
        
        elif weather_type == "all" and self.forecast:
            forecast = self.forecast
            result.append(f"📅 天气预报 - {forecast.city} ({forecast.reporttime})")
            result.append(f"📍 位置: {forecast.province}{forecast.city}")
            result.append("")
            result.append("📊 未来天气预测:")
            for day in forecast.casts:
                result.append(f"  • {day.to_text()}")
        
        elif self.current and self.forecast:
            # 既有实时又有预报
            current = self.current
            forecast = self.forecast
            
            result.append(f"🌤️ 当前天气 - {current.city} ({current.reporttime})")
            result.append(f"📍 位置: {current.province}{current.city}")
            result.append(f"🌡️ 温度: {current.temperature}°C")
            result.append(f"☁️ 天气: {current.weather}")
            result.append(f"💨 风向风力: {current.winddirection}{current.windpower}")
            result.append(f"💧 湿度: {current.humidity}%")
            
            result.append("")
            result.append("📊 未来天气预测:")
            for i, day in enumerate(forecast.casts[:3]):  # 只显示最近3天
                if i == 0:
                    result.append(f"  今天: {day.dayweather} {day.daytemp}°C，夜间{day.nightweather} {day.nighttemp}°C")
                else:
                    result.append(f"  {day.date} ({day.week}): {day.dayweather} {day.daytemp}°C")
        
        else:
            result.append("未获取到天气信息")
        
        return "\n".join(result)

class WeatherMCP:
    """天气查询MCP服务"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_adcode(self, location: str) -> Optional[str]:
        """获取城市编码（adcode）"""
        try:
            # 先尝试地理编码
            geocode_params = {
                "key": AMAP_API_KEY,
                "address": location,
                "output": "json"
            }
            
            response = await self.client.get(f"{AMAP_BASE_URL}/v3/geocode/geo", params=geocode_params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("geocodes"):
                geo = data["geocodes"][0]
                adcode = geo.get("adcode")
                if adcode:
                    return adcode
            
            # 如果地理编码失败，尝试搜索POI
            poi_params = {
                "key": AMAP_API_KEY,
                "keywords": location,
                "output": "json",
                "offset": "1"
            }
            
            response = await self.client.get(f"{AMAP_BASE_URL}/v3/place/text", params=poi_params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("pois"):
                poi = data["pois"][0]
                adcode = poi.get("adcode")
                if adcode:
                    return adcode
            
            # 尝试直接查询城市信息
            district_params = {
                "key": AMAP_API_KEY,
                "keywords": location,
                "subdistrict": "0",  # 不返回下级行政区
                "output": "json"
            }
            
            response = await self.client.get(f"{AMAP_BASE_URL}/v3/config/district", params=district_params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("districts"):
                district = data["districts"][0]
                adcode = district.get("adcode")
                if adcode:
                    return adcode
            
            return None
            
        except Exception as e:
            print(f"获取城市编码错误 {location}: {e}", file=sys.stderr)
            return None
    
    async def get_weather(self, location: str, extensions: WeatherType = WeatherType.BASE) -> WeatherResult:
        """查询天气信息"""
        try:
            # 获取城市编码
            adcode = await self.get_adcode(location)
            
            if not adcode:
                # 如果无法获取adcode，尝试将location作为城市名直接查询
                city_name = location
            else:
                city_name = adcode
            
            # 构建天气查询参数
            params = {
                "key": AMAP_API_KEY,
                "city": city_name,
                "extensions": extensions.value,
                "output": "json"
            }
            
            print(f"调试: 天气查询参数: {params}", file=sys.stderr)
            
            response = await self.client.get(f"{AMAP_BASE_URL}/v3/weather/weatherInfo", params=params)
            data = response.json()
            
            print(f"调试: 天气API响应: {data}", file=sys.stderr)
            
            if data.get("status") != "1":
                # 尝试使用直接的城市名（而不是adcode）
                if adcode and adcode.isdigit():
                    # 可能是adcode格式不对，尝试使用原始location
                    params["city"] = location
                    response = await self.client.get(f"{AMAP_BASE_URL}/v3/weather/weatherInfo", params=params)
                    data = response.json()
                    
                    if data.get("status") != "1":
                        return WeatherResult(
                            status="0",
                            info=data.get("info", "天气查询失败"),
                            infocode=data.get("infocode", "10001")
                        )
            
            # 解析响应
            result = WeatherResult(
                status=data.get("status", "0"),
                info=data.get("info", ""),
                infocode=data.get("infocode", "")
            )
            
            if extensions == WeatherType.BASE:
                # 实况天气
                lives = data.get("lives", [])
                if lives:
                    live = lives[0]
                    result.current = CurrentWeather(
                        province=live.get("province", ""),
                        city=live.get("city", ""),
                        adcode=live.get("adcode", ""),
                        weather=live.get("weather", ""),
                        temperature=live.get("temperature", ""),
                        winddirection=live.get("winddirection", ""),
                        windpower=live.get("windpower", ""),
                        humidity=live.get("humidity", ""),
                        reporttime=live.get("reporttime", "")
                    )
            
            elif extensions == WeatherType.ALL:
                # 预报天气
                forecasts = data.get("forecasts", [])
                if forecasts:
                    forecast_data = forecasts[0]
                    
                    # 解析预报数据
                    casts_data = forecast_data.get("casts", [])
                    casts = []
                    for cast in casts_data:
                        casts.append(ForecastDay(
                            date=cast.get("date", ""),
                            week=cast.get("week", ""),
                            dayweather=cast.get("dayweather", ""),
                            nightweather=cast.get("nightweather", ""),
                            daytemp=cast.get("daytemp", ""),
                            nighttemp=cast.get("nighttemp", ""),
                            daywind=cast.get("daywind", ""),
                            nightwind=cast.get("nightwind", ""),
                            daypower=cast.get("daypower", ""),
                            nightpower=cast.get("nightpower", "")
                        ))
                    
                    result.forecast = WeatherForecast(
                        city=forecast_data.get("city", ""),
                        adcode=forecast_data.get("adcode", ""),
                        province=forecast_data.get("province", ""),
                        reporttime=forecast_data.get("reporttime", ""),
                        casts=casts
                    )
            
            return result
            
        except Exception as e:
            print(f"天气查询错误: {e}", file=sys.stderr)
            return WeatherResult(
                status="0",
                info=f"天气查询异常: {str(e)}",
                infocode="10002"
            )

# 创建FastMCP应用
mcp = FastMCP("amap-weather")

@mcp.tool()
async def get_current_weather(
    location: str
) -> str:
    """
    查询指定地点的实时天气情况
    
    Args:
        location: 城市名称或地区，如'北京'、'苏州市'、'110101'(北京东城区adcode)
    """
    try:
        print(f"调试: 查询实时天气 - 地点: {location}", file=sys.stderr)
        
        weather_service = WeatherMCP()
        result = await weather_service.get_weather(location, WeatherType.BASE)
        
        return result.to_text_summary("base")
        
    except Exception as e:
        print(f"实时天气查询异常: {e}", file=sys.stderr)
        return f"实时天气查询失败: {str(e)}"

@mcp.tool()
async def get_weather_forecast(
    location: str,
    days: int = 3
) -> str:
    """
    查询指定地点的天气预报
    
    Args:
        location: 城市名称或地区，如'北京'、'苏州市'、'110101'(北京东城区adcode)
        days: 预报天数(1-4天)，默认3天
    """
    try:
        print(f"调试: 查询天气预报 - 地点: {location}, 天数: {days}", file=sys.stderr)
        
        weather_service = WeatherMCP()
        result = await weather_service.get_weather(location, WeatherType.ALL)
        
        if result.forecast:
            # 限制返回的天数
            days = max(1, min(days, 4))  # API最多返回4天
            result.forecast.casts = result.forecast.casts[:days]
        
        return result.to_text_summary("all")
        
    except Exception as e:
        print(f"天气预报查询异常: {e}", file=sys.stderr)
        return f"天气预报查询失败: {str(e)}"

@mcp.tool()
async def get_complete_weather(
    location: str
) -> str:
    """
    查询指定地点的完整天气信息（包括实时天气和未来3天预报）
    
    Args:
        location: 城市名称或地区，如'北京'、'苏州市'、'110101'(北京东城区adcode)
    """
    try:
        print(f"调试: 查询完整天气 - 地点: {location}", file=sys.stderr)
        
        weather_service = WeatherMCP()
        
        # 获取实时天气
        current_result = await weather_service.get_weather(location, WeatherType.BASE)
        
        # 获取天气预报
        forecast_result = await weather_service.get_weather(location, WeatherType.ALL)
        
        # 合并结果
        combined_result = WeatherResult(
            status=current_result.status if current_result.status == "1" else forecast_result.status,
            info=current_result.info if current_result.info != "OK" else forecast_result.info,
            infocode=current_result.infocode if current_result.infocode != "10000" else forecast_result.infocode,
            current=current_result.current,
            forecast=forecast_result.forecast
        )
        
        return combined_result.to_text_summary("all")
        
    except Exception as e:
        print(f"完整天气查询异常: {e}", file=sys.stderr)
        return f"完整天气查询失败: {str(e)}"

@mcp.tool()
async def search_city_weather(
    query: str,
    weather_type: WeatherType = WeatherType.BASE,
    limit: int = 5
) -> str:
    """
    搜索城市并查询天气
    
    Args:
        query: 搜索关键词，如'北京'、'苏州'、'上海浦东'等
        weather_type: 天气类型: base(实况天气), all(预报天气)
        limit: 返回结果数量
    """
    try:
        print(f"调试: 搜索城市天气 - 关键词: {query}, 类型: {weather_type}", file=sys.stderr)
        
        weather_service = WeatherMCP()
        
        # 先搜索城市
        params = {
            "key": AMAP_API_KEY,
            "keywords": query,
            "output": "json",
            "offset": str(limit),
            "types": "160100"  # 城市类型
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AMAP_BASE_URL}/v3/place/text", params=params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("pois"):
                pois = data["pois"][:limit]
                result = [f"🔍 搜索 '{query}' 找到以下城市:"]
                
                for i, poi in enumerate(pois, 1):
                    city_name = poi['name']
                    address = poi.get('address', '')
                    adcode = poi.get('adcode', '')
                    
                    result.append(f"\n{i}. {city_name}")
                    if address:
                        result.append(f"   地址: {address}")
                    
                    # 查询该城市的天气
                    try:
                        weather_result = await weather_service.get_weather(city_name, weather_type)
                        if weather_result.status == "1":
                            if weather_type == WeatherType.BASE and weather_result.current:
                                current = weather_result.current
                                result.append(f"   当前天气: {current.weather} {current.temperature}°C")
                            elif weather_type == WeatherType.ALL and weather_result.forecast:
                                forecast = weather_result.forecast
                                today = forecast.casts[0] if forecast.casts else None
                                if today:
                                    result.append(f"   今天: {today.dayweather} {today.daytemp}°C，夜间{today.nightweather} {today.nighttemp}°C")
                        else:
                            result.append(f"   天气查询失败: {weather_result.info}")
                    except Exception as e:
                        result.append(f"   天气查询错误: {str(e)}")
                
                return "\n".join(result)
            else:
                # 如果没有找到城市，直接查询天气
                weather_result = await weather_service.get_weather(query, weather_type)
                return weather_result.to_text_summary(weather_type.value)
                
    except Exception as e:
        return f"城市天气搜索失败: {str(e)}"

# FastMCP会自动处理服务器运行
if __name__ == "__main__":
    mcp.run()