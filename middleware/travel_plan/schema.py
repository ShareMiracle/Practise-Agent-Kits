from pydantic import BaseModel, Field
from typing import List, Union, Literal

class Spot(BaseModel):
    """景点的相关信息"""
    name: str = Field(..., description="景点的名称")
    address: str = Field(..., description="地址")
    description: str = Field(..., description="对景点的简单介绍，控制在25个字以内")
    rating: float = Field(..., description="评分")
    # cost: float = Field(..., description="价格")
    opentime: str = Field(..., description="营业时间")
    times: int = Field(..., description="游玩时长")

class Restraurant(BaseModel):
    """餐厅的相关信息"""
    name: str = Field(..., description="餐厅的名称")
    address: str = Field(..., description="地址")
    description: str = Field(..., description="描述")
    food: str = Field(..., description="特色食物")
    rating: float = Field(..., description="评分")
    cost: float = Field(..., description="价格")

class Hotel(BaseModel):
    """酒店相关信息"""
    name: str = Field(..., description="酒店名称")
    address: str = Field(..., description="地址")
    description: str = Field(..., description="描述")
    rating: float = Field(..., description="评分")
    cost: float = Field(..., description="价格")
    picture: str = Field(..., description="酒店的图片链接，如果没有则为空字符串")

class SpotVisit(BaseModel):
    """景点游玩活动安排，不包括餐饮！"""
    time_period: str = Field(..., description="游玩的具体时间段，例如 '09:00 - 11:30'")
    spot_data: Spot = Field(..., description="对应的景点详细信息")

class Transportation(BaseModel):
    """景点之间的交通方式"""
    mode: Literal["地铁", "步行", "公交", "打车"] = Field(..., description="出行方式")
    duration_minutes: int = Field(..., description="预计耗时(分钟)")
    description: str = Field(..., description="简单的行程描述，例如 '步行：5分钟'、'地铁1号线+换乘3号线：40分钟'、'公交122路：10分钟'")
    # cost: float = Field(0, description="预计交通费用")


class Plan_a_day(BaseModel):
    """一天的规划信息"""
    day_index: int = Field(..., description="第几天")
    timeline: List[Union[SpotVisit, Transportation]] = Field(..., description="按时间顺序排列的行程节点序列")
    

class Plan(BaseModel):
    """完整的旅行规划和建议信息"""
    city: str = Field(..., description="旅行目的地")
    days: int = Field(..., description="旅行天数")
    spots: list[Spot] = Field(..., description="所有在旅行规划中的景点")
    plans: list[Plan_a_day] = Field(..., description="每一天的规划")
    foods: list[str] = Field(..., description="当地特色食物推荐")
    restaurants: list[Restraurant] = Field(..., description="当地餐厅推荐")
    hotels: list[Hotel] = Field(..., description="当地酒店推荐")
    tips: list[str] = Field(..., description="旅行注意事项")
    