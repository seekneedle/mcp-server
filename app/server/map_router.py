from fastmcp import FastMCP
from typing import List, Dict
from utils.log import log
from service.road_map import (
    create_amap,
    create_tmap,
    geocode_amap,
    geocode_tmap,
    get_weather_amap,
    get_weather_tmap,
    get_exchange_rate_amap
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


@map_mcp.tool(name="通过高德地图获取国外地点经纬度")
async def get_international_coordinates(locations: List[str]) -> List[Dict[str, str]]:
    """
    通过高德地图获取国外地点的经纬度信息

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
        return await geocode_amap(locations)
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"获取国外地点坐标失败: {str(e)}, trace: {trace_info}")
        return [{"error": "Service unavailable"} for _ in locations]


@map_mcp.tool(name="通过天地图获取国内地点经纬度")
async def get_domestic_coordinates(locations: List[str]) -> List[Dict[str, str]]:
    """
    通过天地图获取国内地点的经纬度信息

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


@map_mcp.tool(name="通过高德地图获取国外天气")
async def get_international_weather(locations: List[str]) -> List[Dict[str, str]]:
    """
    通过高德地图获取国外天气信息

    参数:
        locations: 地点名称列表，例如: ["巴黎", "纽约"]

    返回:
        包含每个地点天气信息的字典列表，格式:
        [{
            "location": "巴黎",
            "weather": "晴",
            "temperature": "20",
            "wind": "西北风3级",
            "humidity": "45%"
        }]
    """
    try:
        if not locations:
            return []
        log.info(f"获取国外天气: {locations}")
        return await get_weather_amap(locations)
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"获取国外天气失败: {str(e)}, trace: {trace_info}")
        return [{"location": loc, "error": "Service unavailable"} for loc in locations]


@map_mcp.tool(name="通过天地图获取国内天气")
async def get_domestic_weather(locations: List[str]) -> List[Dict[str, str]]:
    """
    通过天地图获取国内天气信息

    参数:
        locations: 地点名称列表，例如: ["北京", "上海"]

    返回:
        包含每个地点天气信息的字典列表，格式:
        [{
            "location": "北京",
            "weather": "晴",
            "temperature": "20",
            "wind": "西北风3级",
            "humidity": "45%"
        }]
    """
    try:
        if not locations:
            return []
        log.info(f"获取国内天气: {locations}")
        return await get_weather_tmap(locations)
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"获取国内天气失败: {str(e)}, trace: {trace_info}")
        return [{"location": loc, "error": "Service unavailable"} for loc in locations]


@map_mcp.tool(name="通过高德地图获取国际汇率")
async def get_international_exchange_rate(currency_pairs: List[str]) -> List[Dict[str, str]]:
    """
    通过高德地图获取国际汇率信息

    参数:
        currency_pairs: 货币对列表，格式为"基础货币_目标货币"，例如: ["USD_CNY", "EUR_CNY"]

    返回:
        包含每个货币对汇率信息的字典列表，格式:
        [{
            "pair": "USD_CNY",
            "rate": "7.2",
            "update_time": "2023-01-01 12:00:00"
        }]
    """
    try:
        if not currency_pairs:
            return []
        log.info(f"获取国际汇率: {currency_pairs}")
        return await get_exchange_rate_amap(currency_pairs)
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"获取国际汇率失败: {str(e)}, trace: {trace_info}")
        return [{"pair": pair, "error": "Service unavailable"} for pair in currency_pairs]

