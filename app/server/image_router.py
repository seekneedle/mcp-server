from fastmcp import FastMCP
from typing import List, Dict
from utils.log import log
from service.image_search import images_search

image_mcp = FastMCP(
    name='image-mcp-server',
    instructions="""
        This server provides image search tool.
    """,
    on_duplicate_tools='ignore'
)


@image_mcp.tool(name="按照关键字列表检索对应的图片")
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
        log.info(f"开始图片搜索，关键字列表: {keywords}, 检索个数: {image_num}")
        results = await images_search(keywords, image_num)
        log.info(f"图片搜索完成，结果: {results}")
        return results
    except Exception as e:
        log.error(f"图片搜索失败: {str(e)}")
        # 返回空字典而不是空列表以保持类型一致性
        return {keyword: [] for keyword in keywords}
