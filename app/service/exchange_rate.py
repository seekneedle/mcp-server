import httpx
from utils.config import config
from utils.log import log
import traceback


async def exchange(src: str, dest: str, money: str) -> str:
    """
    汇率查询，根据货币代码，查询换算金额

    参数:
        src: 转换汇率前的货币代码，如'CNY'
        dest: 转换汇率成的货币代码，如'USD'
        money: 换算金额，如'1'

    返回:
        转换汇率成的货币金额，如'0.139301'
    """
    try:
        async with httpx.AsyncClient(timeout=config['timeout']) as client:
            url = f"https://api.tanshuapi.com/api/exchange/v1/index?key={config['exchange_key']}&from={src}&to={dest}&money={money}"
            response = await client.get(url)
            data = response.json()

            if data and isinstance(data, dict) and data.get("code") == 1:
                return str(data.get("data", {}).get("money", "0"))

            log.error \
                (f"Exchange rate query failed for {src}->{dest}: {data.get('msg', 'Unknown error') if data else 'No response data'}")
            return "0"

    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"Exchange rate query failed for {src}->{dest}: {str(e)}, {trace_info}")
        return "0"