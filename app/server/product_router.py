from fastmcp import FastMCP
from service.product_search import search_by_destination, search_by_pass_through

product_mcp = FastMCP(
    name='product-mcp-server',
    instructions="""
        This server provides travel product related information.
    """,
    on_duplicate_tools='ignore'
)


@product_mcp.tool(name="使用目的地查询旅行产品")
async def search_dest_product_nums(country: str = "", province: str = "", city: str = "", current_page: int=1) -> str:
    """
    使用目的地查询旅行产品

    注意：至少需要提供国家、省份或城市中的一个参数

    Args:
        country: 国家名称 (可选)， 最多只允许有一个国家
        province: 省份名称 (可选)， 最多只允许有一个省份
        city: 城市名称 (可选)， 最多只允许有一个城市
        current_page: 当前查询到的页数，从第1页开始依次查询

    Returns:
        匹配的产品信息，当前查询到第几页，总页数
    """
    return await search_by_destination(country, province, city, current_page)


@product_mcp.tool(name="使用途经地查询旅行产品")
async def search_pass_product_nums(country: str = "", province: str = "", city: str = "", current_page: int=1) -> str:
    """
    使用途经地查询旅行产品

    注意：至少需要提供国家、省份或城市中的一个参数

    Args:
        country: 国家名称 (可选)， 最多只允许有一个国家
        province: 省份名称 (可选)， 最多只允许有一个省份
        city: 城市名称 (可选)， 最多只允许有一个城市
        current_page: 当前查询到的页数，从第1页开始依次查询

    Returns:
        匹配的产品信息，当前查询到第几页，总页数
    """
    return await search_by_pass_through(country, province, city)

