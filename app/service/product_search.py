from typing import List, Dict, Optional
import aiohttp
from utils.config import config
from utils.log import log
from urllib.parse import urlencode
import asyncio


async def product_search(search_args: List[Dict]) -> List[Dict]:
    """
    批量查询并返回原始结果（自动处理分页），优先使用data.pages字段

    Args:
        search_args: 查询参数列表，每个元素格式示例:
            {
                "destCountryCode": "CN",
                "destProvinceCode": "GD",
                "destCityCode": "GZ",
                "current": 1  # 可选分页参数
            }

    Returns:
        所有分页的原始结果合并后的列表
    """
    base_url = config['uux_base_url']
    all_results = []

    async def fetch_page(params: Dict) -> Optional[List[Dict]]:
        """获取单页数据，优先返回data.pages字段"""
        url = f"{base_url}/page?{urlencode(params)}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = (await resp.json()).get('data', {})

                    # 优先返回pages字段，否则返回默认list字段
                    if data is not None and 'pages' in data:
                        return data['pages']
                    return data.get('records', [])

        except Exception as e:
            log.error(f"查询失败: {str(e)}, params: {params}")
            return None

    # 并发处理所有查询条件
    tasks = []
    for arg in search_args:
        # 设置默认分页参数
        params = {
            "current": arg.pop("current", 1),  # 取出current参数，默认第1页
            "pageSize": 100,
            **arg
        }
        tasks.append(fetch_page(params))

    # 并发获取所有页
    pages_results = await asyncio.gather(*tasks)

    # 合并有效结果
    for result in pages_results:
        if isinstance(result, list):
            all_results.extend(result)

    return all_results