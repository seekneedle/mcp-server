import aiohttp
from urllib.parse import urlencode
from utils.config import config
from utils.log import log


async def get_product_info(product_num: str, env: str = 'prod') -> dict:
    """
    异步获取产品信息

    Args:
        product_num: 产品编号
        env: 环境标识 (uat/prod)

    Returns:
        产品信息字典 (API返回的data字段)
        失败时返回空字典
    """
    # 构造请求URL（实际场景中UAT和PROD的域名可能不同）
    base_url = config["uux_base_url"]

    url = f"{base_url}/productInfo?{urlencode({'productNum': product_num})}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return (await response.json()).get('data', {})

    except aiohttp.ClientError as e:
        log.error(f"产品查询失败: {str(e)}, URL: {url}")
    except Exception as e:
        log.error(f"系统异常: {str(e)}")

    return {}  # 失败时返回空字典