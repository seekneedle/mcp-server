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


@product_mcp.tool(name="获取产品的旅行信息")
async def get_product_infos(product_nums: List[str], demand: str) -> List[str]:
    """
    根据产品编号列表检索产品的旅行信息，返回旅行信息

    Args:
        product_nums: 产品编号列表 (如 ["U1001", "U1002"])
        demand: 需要检索产品中的哪些内容

    Returns:
        旅行信息列表
        示例: ["...", ...]
        没有旅行信息时返回空列表
    """
    # 并发获取所有产品信息
    product_infos = await asyncio.gather(*[get_product_info(num) for num in product_nums])

    trip_list = await parse_product_info(product_infos, demand)

    return trip_list

