from fastmcp import FastMCP
from typing import List, Dict
from utils.log import log
from service.road_map import (
    create_tmap,
    geocode_weather,
    get_weather_by_coordinates
)
import traceback

map_mcp = FastMCP(
    name='map-mcp-server',
    instructions="""
        This server provides map related tool.
    """,
    on_duplicate_tools='ignore'
)


@map_mcp.tool(name="按照途径点生成路书地图")
async def generate_domestic_itinerary(locations: List[Dict[str, str]]) -> str:
    """
    按照途径点生成路书地图

    参数:
        locations: 地点信息列表，每个地点包含name(名称)、lng(经度)、lat(纬度)、desc(描述)
           示例: [{"name": "北京", "lng": "116.407", "lat": "39.904", "desc": "中国首都,..."}]

    返回:
        生成的HTML路书地图文件路径，失败时返回空字符串
    """
    try:
        if not locations:
            return ""
        log.info(f"生成旅行地图: {locations}")
        return await create_tmap(locations)

    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"生成旅行地图失败: {str(e)}, trace: {trace_info}")
        return ""


@map_mcp.tool(name="获取地点经纬度")
async def get_coordinates(locations: List[str]) -> List[Dict[str, str]]:
    """
    获取地点的经纬度信息

    参数:
        locations: 地点名称列表，要求采用城市名和国家名(ISO 3166-1)，中间用逗号分隔，例如: ["Tianjin,CN", "London,GB"]

    返回:
        包含每个地点经纬度信息的字典列表，格式:
        [{"name": "天津市", "lng": "39.1175488", "lat": "117.1913008"}]
    """
    try:
        if not locations:
            return []
        log.info(f"获取国内地点坐标: {locations}")
        return await geocode_weather(locations)
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"获取国内地点坐标失败: {str(e)}, trace: {trace_info}")
        return [{"error": "Service unavailable"} for _ in locations]


@map_mcp.tool(name="查询坐标点指定日期的天气信息")
async def query_weather_by_coordinates(lat: float, lon: float, date: str, tz: str = "+08:00", units: str = "metric") -> Dict:
    """
    查询坐标点指定日期的天气信息

    参数:
        lat: 纬度
        lon: 经度
        date: 日期，格式为YYYY-MM-DD
        tz: 时区偏移，格式为±HH:MM (默认"+08:00")
        units: 单位制 ("metric"或"imperial"，默认"metric")

    返回:
        包含天气信息的字典，包括温度、降水、风速等数据
        示例:
        {
            "lat": 60.45,
            "lon": -38.67,
            "tz": "+03:00",
            "date": "2025-07-30",
            "units": "metric",
            "temperature": {
                "min": 10.93,
                "max": 12.29,
                "afternoon": 11.44,
                ...
            },
            ...
        }
    """
    try:
        return await get_weather_by_coordinates(lat, lon, date, tz, units)
    except Exception as e:
        trace_info = traceback.format_exc()
        error_msg = f"Weather query failed: {str(e)}"
        log.error(f"{error_msg}, trace: {trace_info}")
        return {"error": error_msg}