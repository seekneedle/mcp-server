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
async def generate_map(markers: List[str], lines: List[str]=[]) -> str:
    """
    按照途经点生成路书地图

    参数:
        markers: 在地图上的标记点的名称和坐标，每个标记点格式为"名称,经度,纬度"，同一个地点坐标合并到一个标记点。
           示例: ["第1天和第7天北京,116.407,39.904", "第2-6天上海,121.473,31.230"]
        lines: 按照途径点行程顺序的线路首尾坐标（线路没有方向，因此首位坐标互换如果相同，只需要保留一条线路信息，若只有一个marker，则lines为空列表），每条线路的格式为"首节点经度,首节点纬度,尾节点经度,尾节点纬度"。
           示例: ["116.407,39.904,121.473,31.230"]

    返回:
        生成的HTML路书地图文件路径，失败时返回空字符串
    """
    try:
        if not markers:
            log.info("生成旅行地图异常，输入markers为空")
            return ""

        log.info(f"生成旅行地图 markers: {markers}， lines: {lines}")

        # 处理标记点
        processed_markers = []
        for marker_str in markers:
            try:
                # 分割字符串为名称、经度、纬度三部分
                parts = marker_str.split(',', 2)  # 最多分割成3部分
                if len(parts) != 3:
                    log.error(f"无效的标记点格式: {marker_str}")
                    continue

                name, lng, lat = parts
                processed_markers.append({
                    "name": name.strip(),
                    "lng": lng.strip(),
                    "lat": lat.strip()
                })
            except Exception as e:
                log.error(f"解析标记点失败: {marker_str}, 错误: {str(e)}")

        if not processed_markers:
            log.error("无有效标记点数据")
            return ""

        log.info(f"转换后的标记点数据: {processed_markers}")

        # 处理线路
        processed_lines = []
        for line_str in lines:
            try:
                # 分割字符串为起点经度、起点纬度、终点经度、终点纬度
                parts = line_str.split(',')
                if len(parts) != 4:
                    log.error(f"无效的线路格式: {line_str}")
                    continue

                start_lng, start_lat, end_lng, end_lat = parts
                processed_lines.append({
                    "start_lng": start_lng.strip(),
                    "start_lat": start_lat.strip(),
                    "end_lng": end_lng.strip(),
                    "end_lat": end_lat.strip()
                })
            except Exception as e:
                log.error(f"解析线路失败: {line_str}, 错误: {str(e)}")

        log.info(f"转换后的线路数据: {processed_lines}")

        return await create_tmap(processed_markers, processed_lines)

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