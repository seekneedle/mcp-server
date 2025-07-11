from fastmcp import FastMCP
from typing import List, Dict
from utils.log import log
from service.road_map import (
    create_amap,
    create_tmap,
    geocode_openai,
    geocode_tmap
)
import traceback

map_mcp = FastMCP(
    name='map-mcp-server',
    instructions="""
        This server provides map related tool.
    """,
    on_duplicate_tools='ignore'
)


@map_mcp.tool(name="按照国外旅行路径生成路书地图")
async def generate_travel_itinerary(locations: List[Dict[str, str]]) -> str:
    """
    按照国外旅行路径生成路书地图

    参数:
        locations: 地点信息列表，每个地点包含name(名称)、lng(经度)、lat(纬度)、desc(描述)
           示例: [{"name": "巴黎", "lng": "2.3522", "lat": "48.8566", "desc": "法国首都"}]

    返回:
        生成的HTML路书地图文件路径，失败时返回空字符串
    """
    try:
        if not locations:
            return ""

        log.info(f"生成国外旅行地图: {locations}")
        return await create_amap(locations)

    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"生成国外旅行地图失败: {str(e)}, trace: {trace_info}")
        return ""

@map_mcp.tool(name="按照国内旅行路径生成路书地图")
async def generate_domestic_itinerary(locations: List[Dict[str, str]]) -> str:
    """
    按照国内旅行路径生成路书地图

    参数:
        locations: 地点信息列表，每个地点包含name(名称)、lng(经度)、lat(纬度)、desc(描述)
           示例: [{"name": "北京", "lng": "116.407", "lat": "39.904", "desc": "中国首都"}]

    返回:
        生成的HTML路书地图文件路径，失败时返回空字符串
    """
    try:
        if not locations:
            return ""
        log.info(f"生成国内旅行地图: {locations}")
        return await create_tmap(locations)

    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"生成国内旅行地图失败: {str(e)}, trace: {trace_info}")
        return ""


@map_mcp.tool(name="获取国外地点经纬度")
async def get_international_coordinates(locations: List[str]) -> List[Dict[str, str]]:
    """
    获取国外地点的经纬度信息

    参数:
        locations: 地点名称列表，例如: ["巴黎", "纽约"]

    返回:
        包含每个地点经纬度信息的字典列表，格式:
        [{"name": "巴黎", "lng": "2.3522", "lat": "48.8566", "desc": "Geocoded location: 巴黎"}]
    """
    try:
        if not locations:
            return []
        log.info(f"获取国外地点坐标: {locations}")
        return await geocode_openai(locations)
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"获取国外地点坐标失败: {str(e)}, trace: {trace_info}")
        return [{"error": "Service unavailable"} for _ in locations]


@map_mcp.tool(name="获取国内地点经纬度")
async def get_domestic_coordinates(locations: List[str]) -> List[Dict[str, str]]:
    """
    获取国内地点的经纬度信息

    参数:
        locations: 地点名称列表，例如: ["北京", "上海"]

    返回:
        包含每个地点经纬度信息的字典列表，格式:
        [{"name": "北京", "lng": "116.407", "lat": "39.904", "desc": "Geocoded location: 北京"}]
    """
    try:
        if not locations:
            return []
        log.info(f"获取国内地点坐标: {locations}")
        return await geocode_tmap(locations)
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"获取国内地点坐标失败: {str(e)}, trace: {trace_info}")
        return [{"error": "Service unavailable"} for _ in locations]

