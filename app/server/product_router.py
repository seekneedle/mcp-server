from fastmcp import FastMCP
from typing import List, Dict
from utils.geo import get_city_code, get_province_code, get_country_code
from service.product_search import product_search
from service.product_detail import get_product_info
from utils.log import log
import traceback
import asyncio
from service.product_feature_search import get_feature_desc
from service.image_search import images_search

product_mcp = FastMCP(
    name='product-mcp-server',
    instructions="""
        This server provides travel product related information.
    """,
    on_duplicate_tools='ignore'
)


async def _search_product_nums(location_dict: Dict[str, str], search_type: str) -> List[str]:
    """
    根据地理信息查询产品编号的公共方法

    Args:
        location_dict: 包含地理信息的字典
        search_type: 查询类型，'dest'或'pass'

    Returns:
        匹配的产品编号列表
    """
    # 参数校验
    if not location_dict or not any(location_dict.values()):
        return []

    # 获取各级地理编码（空值自动处理）
    country = location_dict.get("country", "")
    province = location_dict.get("province", "")
    city = location_dict.get("city", "")

    # 根据查询类型构建参数前缀
    prefix = "dest" if search_type == "dest" else "pass"

    # 构建查询参数
    search_args = [{
        f"{prefix}CountryCode": get_country_code(country) if country else "",
        f"{prefix}ProvinceCode": get_province_code(province) if province else "",
        f"{prefix}CityCode": get_city_code(city) if city else ""
    }]

    log.info(f"Search args: {search_args}")

    try:
        # 调用产品搜索服务
        results = await product_search(search_args)

        log.info(f"Search results: {results}")
        
        # 提取产品编号
        return [item["productNum"] for item in results if item.get("productNum")]
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"产品查询失败: {str(e)}, trace info: {trace_info}")
        return []


@product_mcp.tool(name="使用目的地查询旅行产品的产品编号")
async def search_dest_product_nums(location_dict: Dict[str, str]) -> List[str]:
    """
    根据目的地查询产品编号

    Args:
        location_dict: 包含地理信息的字典， 包含三个key：country， province， city

    Returns:
        匹配的产品编号列表
    """
    return await _search_product_nums(location_dict, "dest")


@product_mcp.tool(name="使用途经地查询旅行产品的产品编号")
async def search_pass_product_nums(location_dict: Dict[str, str]) -> List[str]:
    """
    根据途经地查询产品编号

    Args:
        location_dict: 包含地理信息的字典， 包含三个key：country， province， city

    Returns:
        匹配的产品编号列表
    """
    return await _search_product_nums(location_dict, "pass")


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


@product_mcp.tool(name="按照关键字列表检索对应的图片")
async def keyword_image_search(keywords: List[str], image_num: int=3) -> Dict[str, List[str]]:
    """
    根据关键字列表搜索对应的图片

    参数:
        keywords: 要搜索的关键字列表
        image_num: 每个关键字检索到的图片数量

    返回:
        字典格式结果，key为关键字，value为对应的图片路径列表
    """
    try:
        log.info(f"开始图片搜索，关键字列表: {keywords}")
        results = await images_search(keywords, image_num)
        log.info(f"图片搜索完成，结果数量: {sum(len(v) for v in results.values())}")
        return results
    except Exception as e:
        log.error(f"图片搜索失败: {str(e)}")
        # 返回空字典而不是空列表以保持类型一致性
        return {keyword: [] for keyword in keywords}
