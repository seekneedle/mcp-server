from fastmcp import FastMCP
from utils.log import log
from service.exchange_rate import exchange
import traceback
import time  # 新增导入time模块

exchange_mcp = FastMCP(
    name='exchange-mcp-server',
    instructions="""
        This server provides exchange rate search.
    """,
    on_duplicate_tools='ignore'
)


@exchange_mcp.tool(name="根据货币代码查询汇率")
async def exchange_rate(src: str="CNY", dest: str="USD", money: str="1") -> str:
    """
    汇率查询，根据货币代码，查询换算金额

    参数:
        src: 转换汇率前的货币代码，如‘CNY’
        dest: 转换汇率成的货币代码，如‘USD’
        money: 换算金额，如‘1’

    返回:
        转换汇率成的货币金额，如‘0.139301’
    """
    start_time = time.time()  # 记录开始时间
    try:
        log.info(f"Starting exchange_rate - src: {src}, dest: {dest}, money: {money}")
        result = await exchange(src, dest, money)
        log.info(f"汇率换算完成，结果: {result}")
        return result
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"视频搜索失败: {str(e)}, trace: {trace_info}")
        # 返回空字典而不是空列表以保持类型一致性
        return "0"
    finally:
        duration = time.time() - start_time  # 计算耗时
        log.info(f"Completed exchange_rate - src: {src}, dest: {dest}, money: {money}, duration: {duration}")  # 记录耗时