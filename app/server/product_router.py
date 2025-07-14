from fastmcp import FastMCP
from typing import List
from service.product_search import search_by_destination, search_by_pass_through
from service.product_detail import get_product_info
from utils.log import log
import traceback
from service.product_detail import parse_product_info
import asyncio

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
        country: 国家名称 (可选)， 最多只允许有一个国家
        province: 省份名称 (可选)， 最多只允许有一个省份
        city: 城市名称 (可选)， 最多只允许有一个城市

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
        country: 国家名称 (可选)， 最多只允许有一个国家
        province: 省份名称 (可选)， 最多只允许有一个省份
        city: 城市名称 (可选)， 最多只允许有一个城市

    Returns:
        匹配的产品编号列表
    """
    return await search_by_pass_through(country, province, city)


# @product_mcp.tool(name="获取产品的旅行信息")
async def get_product_infos(product_nums: List[str], demand: str) -> str:
    """
    根据产品编号列表和具体出行需求检索产品的旅行信息，返回旅行信息，如往返机票，景点，酒店，购物，交通信息

    Args:
        product_nums: 产品编号列表 (如 ["U1001", "U1002"])
        demand: 出行需求和根据出行需求需要检索产品中的哪些内容（比如根据出行目的地，想看的景点等）

    Returns:
        按照用户需求获取的旅行信息
    """
    # 并发获取所有产品信息
    product_infos = await asyncio.gather(*[get_product_info(num) for num in product_nums])

    trip_info = await parse_product_info(product_infos, demand)

    return trip_info

@product_mcp.tool(name="根据产品编号和城市列表检索景点信息")
async def get_scenic_spots_by_cities(product_nums: List[str], cities: List[str]) -> str:
    """
    根据产品编号和城市列表检索景点信息

    Args:
        product_nums: 产品编号列表 (如 ["U1001", "U1002"])
        cities: 城市名称列表 (如 ["巴黎", "伦敦"])

    Returns:
        返回格式为"景点名称-所属城市-产品编号"的字符串列表
    """
    demand = f"请提取以下城市的景点信息：{', '.join(cities)}，返回格式为'景点名称-所属城市-产品编号'"
    return await get_product_infos(product_nums, demand)


@product_mcp.tool(name="根据产品编号和地点检索航班信息")
async def get_flight_info(product_nums: List[str],
                          departure_country: str = "",
                          departure_city: str = "",
                          arrival_country: str = "",
                          arrival_city: str = "") -> str:
    """
    根据产品编号和出发地/目的地检索航班信息

    Args:
        product_nums: 产品编号列表
        departure_country: 出发国家 (可选)
        departure_city: 出发城市 (可选)
        arrival_country: 到达国家 (可选)
        arrival_city: 到达城市 (可选)

    Returns:
        字符串格式的航班信息
    """
    demand_parts = []
    if departure_country or departure_city:
        demand_parts.append(f"出发地：{departure_country or ''}{departure_city or ''}")
    if arrival_country or arrival_city:
        demand_parts.append(f"目的地：{arrival_country or ''}{arrival_city or ''}")

    demand = f"请提取航班信息，{'，'.join(demand_parts)}。包括航空公司、航班号、起降时间和机场信息"
    return await get_product_infos(product_nums, demand)


@product_mcp.tool(name="根据产品编号和地点检索酒店信息")
async def get_hotel_info(product_nums: List[str], country: str = "", city: str = "") -> str:
    """
    根据产品编号和地点检索酒店信息

    Args:
        product_nums: 产品编号列表
        country: 国家名称 (可选)
        city: 城市名称 (可选)

    Returns:
        字符串格式的酒店信息
    """
    location = ""
    if country and city:
        location = f"{country}{city}"
    elif country:
        location = country
    elif city:
        location = city

    demand = f"请提取{location}的酒店信息，包括酒店名称、星级和地址"
    return await get_product_infos(product_nums, demand)


@product_mcp.tool(name="根据产品编号和地点检索购物商店信息")
async def get_shopping_info(product_nums: List[str], country: str = "", city: str = "") -> str:
    """
    根据产品编号和地点检索购物商店信息

    Args:
        product_nums: 产品编号列表
        country: 国家名称 (可选)
        city: 城市名称 (可选)

    Returns:
        字符串格式的购物商店信息
    """
    location = ""
    if country and city:
        location = f"{country}{city}"
    elif country:
        location = country
    elif city:
        location = city

    demand = f"请提取{location}的购物商店信息，包括商店名称、主营商品和描述"
    return await get_product_infos(product_nums, demand)


@product_mcp.tool(name="根据产品编号和国家检索旅行注意事项")
async def get_travel_notices(product_nums: List[str], country: str) -> str:
    """
    根据产品编号和国家检索旅行注意事项

    Args:
        product_nums: 产品编号列表
        country: 国家名称

    Returns:
        字符串格式的旅行注意事项
    """
    demand = f"请提取{country}的旅行注意事项，包括签证、安全、健康、风俗等信息"
    return await get_product_infos(product_nums, demand)