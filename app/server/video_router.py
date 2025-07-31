from fastmcp import FastMCP
from typing import List, Dict
from utils.log import log
from service.video_search import videos_search
import traceback
import time  # 新增导入time模块

video_mcp = FastMCP(
    name='video-mcp-server',
    instructions="""
        This server provides video search tool.
    """,
    on_duplicate_tools='ignore'
)


@video_mcp.tool(name="按照关键字列表检索对应的视频")
async def keyword_video_search(keywords: List[str], video_num: int=3) -> Dict[str, List[str]]:
    """
    根据关键字列表搜索对应的视频

    参数:
        keywords: 要搜索的关键字列表
        video_num: 每个关键字检索到的视频数量

    返回:
        字典格式结果，key为关键字，value为对应的视频路径列表
    """
    start_time = time.time()  # 记录开始时间
    try:
        log.info(f"Starting keyword_video_search - keywords: {keywords}, video_num: {video_num}")
        results = await videos_search(keywords, video_num)
        log.info(f"视频搜索完成，结果: {results}")
        return results
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"视频搜索失败: {str(e)}, trace: {trace_info}")
        # 返回空字典而不是空列表以保持类型一致性
        return {keyword: [] for keyword in keywords}
    finally:
        duration = time.time() - start_time  # 计算耗时
        log.info(f"Completed keyword_video_search in {duration:.2f} seconds")  # 记录耗时