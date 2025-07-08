from fastmcp import FastMCP
from typing import List, Dict
from utils.log import log
from service.road_map import create_road_map

map_mcp = FastMCP(
    name='map-mcp-server',
    instructions="""
        This server provides map related tool.
    """,
    on_duplicate_tools='ignore'
)


@map_mcp.tool(name="按照旅行路径生成路书地图")
async def keyword_image_search(pass_locations: List[str]) -> str:
    """
    按照旅行路径生成路书地图

    参数:
        pass_locations: 途径点名称

    返回:
        路书地图
    """
    try:
        log.info(f"开始生成路书地图，途径点列表: {pass_locations}")
        results = await create_road_map(pass_locations)
        log.info(f"生成路书地图完成，结果: {results}")
        return results
    except Exception as e:
        log.error(f"生成路书地图失败: {str(e)}")
        # 返回空
        return ''
