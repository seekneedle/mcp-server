from fastmcp import FastMCP
from typing import List
from service.product_search import search_by_destination, search_by_pass_through
from service.product_detail import get_product_info
from utils.log import log
import traceback
import asyncio
from service.product_feature_search import get_feature_desc

product_mcp = FastMCP(
    name='product-mcp-server',
    instructions="""
        This server provides travel product related information.
    """,
    on_duplicate_tools='ignore'
)


@product_mcp.tool(name="使用目的地查询旅行产品的产品编号")
async def search_dest_product_nums(country: str = "", province: str = "", city: str = "") -> List[str]:
    """
    根据目的地查询产品编号

    注意：至少需要提供国家、省份或城市中的一个参数

    Args:
        country: 国家名称 (可选)
        province: 省份名称 (可选)
        city: 城市名称 (可选)

    Returns:
        匹配的产品编号列表
    """
    return await search_by_destination(country, province, city)


@product_mcp.tool(name="使用途经地查询旅行产品的产品编号")
async def search_pass_product_nums(country: str = "", province: str = "", city: str = "") -> List[str]:
    """
    根据途经地查询产品编号

    注意：至少需要提供国家、省份或城市中的一个参数

    Args:
        country: 国家名称 (可选)
        province: 省份名称 (可选)
        city: 城市名称 (可选)

    Returns:
        匹配的产品编号列表
    """
    return await search_by_pass_through(country, province, city)


@product_mcp.tool(name="获取产品的旅行信息")
async def get_product_infos(product_nums: List[str]) -> List[str]:
    """
    根据产品编号列表检索产品的旅行信息，返回旅行信息

    Args:
        product_nums: 产品编号列表 (如 ["U1001", "U1002"])

    Returns:
        旅行信息列表
        示例: ["...", ...]
        没有旅行信息时返回空列表
    """
    trip_list = []

    # 并发获取所有产品信息
    product_infos = await asyncio.gather(*[get_product_info(num) for num in product_nums])

    for product_info in product_infos:
        if not product_info:
            continue

        # 提取所有旅行信息
        try:
            # 遍历所有线路
            for line in product_info.get("lineList", []):
                log.info(f"线路信息: {line}")
                traffic_infos = []
                traffic_infos.append(get_feature_desc(line, "去程交通", 'goTransportName'))
                traffic_infos.append(get_feature_desc(line,
                                                         "去程航班（如果去程交通是飞机时，包括航空公司编码、航空公司名称、航班号、启程机场编码、去程机场名称、启程出发时间、到达机场编码、到达机场名称、到达时间、日期差、航班顺序）",
                                                         'goAirports',
                                                         ["airlineCode", "airlineName", "flightNo", "startAirportCode",
                                                          "startAirportName", "startTime", "arriveAirportCode",
                                                          "arriveAirportName", "arriveTime", "days", "flightSort"]))
                traffic_infos.append(get_feature_desc(line, "回程交通", 'backTransportName'))
                traffic_infos.append(get_feature_desc(line,
                                                         "回程航班（如果回程交通是飞机时，包括航空公司编码、航空公司名称、航班号、回程机场编码、回程机场名称、回程出发时间、到达机场编码、到达机场名称、到达时间、日期差、航班顺序）",
                                                         'backAirports',
                                                         ["airlineCode", "airlineName", "flightNo", "startAirportCode",
                                                          "startAirportName", "startTime", "arriveAirportCode",
                                                          "arriveAirportName", "arriveTime", "days", "flightSort"]))
                traffic_infos = "\n".join(traffic_infos)
                trip_list.append(traffic_infos)
                log.info(f"交通航班信息: {traffic_infos}")
                try:
                    # 遍历线路中的每一天行程
                    for trip in line.get("trips", []):
                        log.info(f"行程信息: {trip}")
                        trip_infos = []
                        trip_infos.append(get_feature_desc(trip, "行程内容描述", 'content'))
                        trip_infos.append(get_feature_desc(trip, "当天行程-交通信息（出发地、出发时间、目的地、到达时间、交通类型，bus-大巴；minibus-中巴；train-火车；ship-轮船；liner-游轮；airplane-飞机；99-其他；、）", 'scheduleTraffics',
                                                                         ["departure", "departureTime", "destination",
                                                                          "arrivalTime", "trafficType"]))
                        trip_infos.append(get_feature_desc(trip, "酒店信息（酒店名称、星级 1 一星 2 两星 3 三星 4 四星 5 五星）", 'hotels', ["name", "star"]))
                        trip_infos.append(get_feature_desc(trip, "特色商店（商店名称、特色产品、商店介绍）", 'stores', ["name", "mainProducts", "description"]))
                        trip_list.append("\n".join(trip_infos))
                except Exception as e:
                    trace_info = traceback.format_exc()
                    log.error(f"行程提取失败: {str(e)}, trace: {trace_info}")

        except Exception as e:
            trace_info = traceback.format_exc()
            log.error(f"旅行信息提取失败: {str(e)}, trace: {trace_info}")

    return trip_list

