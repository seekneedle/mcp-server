from fastmcp import FastMCP
from service.product_search import search_by_detail, search_by_abs, get_product_features
from utils.log import log
import time

product_mcp = FastMCP(
    name='product-mcp-server',
    instructions="""
        This server provides travel product related information.
    """,
    on_duplicate_tools='ignore'
)

product_mcp_2 = FastMCP(
    name='product-mcp-server',
    instructions="""
        This server provides travel product related information.
    """,
    on_duplicate_tools='ignore'
)

@product_mcp_2.tool(name="使用目的地查询旅行产品框架")
async def search_dest_product_abstract(country: str = "", province: str = "", city: str = "", current_page: int=1) -> str:
    """
    使用目的地查询旅行产品框架，返回信息包不包含景点酒店机票的具体描述

    注意：至少需要提供国家、省份或城市中的一个参数，优先使用城市查询，如果城市查不到，再更换为省份、国家。

    Args:
        country: 国家名称 (可选)， 每次输入最多只允许有一个国家，不允许同时查多个国家
        province: 省份名称 (可选)， 每次输入最多只允许有一个省份，不允许同时查多个省份
        city: 城市名称 (可选)， 每次输入最多只允许有一个城市，不允许同时查多个城市
        current_page: 当前查询到的页数，从第1页开始依次查询

    Returns:
        匹配的产品框架，不包括景点酒店机票的具体描述，当前查询到第几页，总页数
    """
    start_time = time.time()
    try:
        log.info(f"Starting search_dest_product_abstract - country: {country}, province: {province}, city: {city}, page: {current_page}")
        result = await search_by_abs(country, province, city, current_page)
        return result
    finally:
        duration = time.time() - start_time
        log.info(f"Completed search_dest_product_abstract in {duration:.2f} seconds")

@product_mcp.tool(name="使用目的地查询旅行产品详情")
async def search_dest_product_details(country: str = "", province: str = "", city: str = "", current_page: int=1) -> str:
    """
    使用目的地查询旅行产品详情，返回信息包含景点酒店机票的具体描述

    注意：至少需要提供国家、省份或城市中的一个参数，优先使用城市查询，如果城市查不到，再更换为省份、国家。

    Args:
        country: 国家名称 (可选)， 每次输入最多只允许有一个国家，不允许同时查多个国家
        province: 省份名称 (可选)， 每次输入最多只允许有一个省份，不允许同时查多个省份
        city: 城市名称 (可选)， 每次输入最多只允许有一个城市，不允许同时查多个城市
        current_page: 当前查询到的页数，从第1页开始依次查询

    Returns:
        匹配的产品信息，包括景点酒店机票的具体描述，当前查询到第几页，总页数
    """
    start_time = time.time()
    try:
        log.info(f"Starting search_dest_product_details - country: {country}, province: {province}, city: {city}, page: {current_page}")
        return await search_by_detail(country, province, city, current_page)
    finally:
        duration = time.time() - start_time
        log.info(f"Completed search_dest_product_details in {duration:.2f} seconds")


# @product_mcp.tool(name="使用途经地查询旅行产品")
# async def search_pass_product_nums(country: str = "", province: str = "", city: str = "", current_page: int=1) -> str:
#     """
#     使用途经地查询旅行产品
#
#     注意：至少需要提供国家、省份或城市中的一个参数
#
#     Args:
#         country: 国家名称 (可选)， 最多只允许有一个国家
#         province: 省份名称 (可选)， 最多只允许有一个省份
#         city: 城市名称 (可选)， 最多只允许有一个城市
#         current_page: 当前查询到的页数，从第1页开始依次查询
#
#     Returns:
#         匹配的产品信息，当前查询到第几页，总页数
#     """
#     start_time = time.time()
#     try:
#         log.info(f"Starting search_pass_product_nums - country: {country}, province: {province}, city: {city}, page: {current_page}")
#         return await search_by_pass_through(country, province, city)
#     finally:
#         duration = time.time() - start_time
#         log.info(f"Completed search_pass_product_nums in {duration:.2f} seconds")


@product_mcp_2.tool(name="使用产品编号查询旅行产品详情")
async def search_by_product_num(product_num: str) -> str:
    """
    使用产品编号查询旅行产品的详情，返回信息包含景点酒店机票的具体描述

    注意：至少需要提供国家、省份或城市中的一个参数，优先使用城市查询，如果城市查不到，在更换为省份、国家。

    Args:
        product_num: 产品编号，如U123456

    Returns:
        匹配的产品信息，包括景点酒店机票的具体描述
    """
    start_time = time.time()
    try:
        log.info(f"Starting search_by_product_num - product_num: {product_num}")
        return await get_product_features(product_num)
    finally:
        duration = time.time() - start_time
        log.info(f"Completed search_by_product_num in {duration:.2f} seconds")