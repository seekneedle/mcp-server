from fastmcp import FastMCP
from typing import List, Dict
from utils.log import log
from service.road_map import (
    create_tmap,
    geocode_weather,
    get_weather
)
import traceback

map_mcp = FastMCP(
    name='map-mcp-server',
    instructions="""
        This server provides map related tool.
    """,
    on_duplicate_tools='ignore'
)


@map_mcp.tool(name="按照途经点生成路书地图")
async def generate_itinerary(locations: List[str]) -> str:
    """
    按照途经点生成路书地图

    参数:
        locations: 地点信息字符串列表，每个字符串格式为"名称,经度,纬度"
           示例: ["北京,116.407,39.904", "上海,121.473,31.230"]

    返回:
        生成的HTML路书地图文件路径，失败时返回空字符串
    """
    try:
        if not locations:
            log.info("生成旅行地图异常，输入locations为空")
            return ""

        log.info(f"生成旅行地图: {locations}")

        # 将字符串列表转换为create_tmap所需的字典格式
        processed_locations = []
        for loc_str in locations:
            try:
                # 分割字符串为名称、经度、纬度三部分
                parts = loc_str.split(',', 2)  # 最多分割成3部分
                if len(parts) != 3:
                    log.error(f"无效的地点格式: {loc_str}")
                    continue

                name, lng, lat = parts
                processed_locations.append({
                    "name": name.strip(),
                    "lng": lng.strip(),
                    "lat": lat.strip()
                })
            except Exception as e:
                log.error(f"解析地点失败: {loc_str}, 错误: {str(e)}")

        if not processed_locations:
            log.error("无有效地点数据")
            return ""

        log.info(f"转换后的地点数据: {processed_locations}")
        return await create_tmap(processed_locations)

    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"生成旅行地图失败: {str(e)}, trace: {trace_info}")
        return ""


@map_mcp.tool(name="获取地点经纬度")
async def get_coordinates(locations: List[str]) -> List[Dict[str, str]]:
    """
    获取地点的经纬度信息

    参数:
        locations: 地点名称列表，要求采用城市名(有限使用英文，没有找到英文经纬度再尝试其他语言城市名)和国家名(ISO 3166-1)，中间用逗号分隔，例如: ["Tianjin,CN", "London,GB"]

    返回:
        包含每个地点经纬度信息的字典列表，格式:
        [{"name": "天津市", "lng": "39.1175488", "lat": "117.1913008"}]
    """
    try:
        if not locations:
            return []
        log.info(f"获取地点坐标: {locations}")
        return await geocode_weather(locations)
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"获取地点坐标失败: {str(e)}, trace: {trace_info}")
        return [{"error": "Service unavailable"} for _ in locations]


@map_mcp.tool(name="查询多个地点指定日期的天气信息")
async def query_weather_for_coordinates(coordinates: List[Dict[str, str]]) -> List[Dict]:
    """
    查询多个地点(带日期)的天气信息

    参数:
        coordinates: 地点信息列表，每个地点包含:
            - lat: 纬度
            - lon: 经度
            - date: 日期(格式可以是YYYY-MM-DD、MM-DD或DD)
        示例: [
            {"lat": "43.941", "lon": "110.491", "date": "2025-07-15"},
            {"lat": "39.904", "lon": "116.407", "date": "07-15"},
            {"lat": "31.230", "lon": "121.474", "date": "15"}
        ]

    返回:
        天气信息列表，每个元素对应一个地点的天气数据
        示例: [
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
            },
            ...
        ]
    """
    try:
        return await get_weather(coordinates)
    except Exception as e:
        trace_info = traceback.format_exc()
        error_msg = f"Location weather query failed: {str(e)}"
        log.error(f"{error_msg}, trace: {trace_info}")
        return []