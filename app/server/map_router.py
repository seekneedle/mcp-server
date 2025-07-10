from fastmcp import FastMCP
from typing import List, Dict
from utils.log import log
from service.road_map import create_amap, create_tmap
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
