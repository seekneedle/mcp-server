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
                "destCityCode": "GZ"
            }

    Returns:
        所有分页的原始结果合并后的列表
    """
    base_url = config['uux_base_url']
    all_results = []

    async def fetch_data(params: Dict) -> Optional[Dict]:
        """获取单页数据，返回整个响应数据字典"""
        url = f"{base_url}/page?{urlencode(params)}"
        log.info(f"Fetching data from: {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as e:
            log.error(f"查询失败: {str(e)}, params: {params}")
            return None

    async def process_search_args(args: Dict) -> List[Dict]:
        """处理单个查询参数，获取所有分页数据"""
        # 1. 获取第一页数据并确定总页数
        first_page_params = {
            "current": 1,
            "pageSize": 10,
            **args
        }
        
        first_page_data = await fetch_data(first_page_params)
        if not first_page_data or 'data' not in first_page_data:
            log.error(f"获取第一页数据失败: {args}")
            return []
        
        data = first_page_data['data']
        
        # 确定总页数
        total_pages = data.get('pages', 1)
        
        # 提取第一页结果
        results = []
        records = data.get('records', [])
        log.error(f"获取第1页数据: {records}")
        results.extend(records)
        
        # 2. 准备剩余页的查询任务
        tasks = []
        for page in range(2, total_pages + 1):
            task_params = {
                "current": page,
                "pageSize": 10,
                **args
            }
            tasks.append(fetch_data(task_params))
        
        # 3. 并发获取剩余页数据
        if tasks:
            pages_data = await asyncio.gather(*tasks)
            for page_data in pages_data:
                if page_data and 'data' in page_data:
                    page_records = data.get('records', [])
                    log.error(f"获取第{data.get('current', 2)}页数据: {records}")
                    results.extend(page_records)
        
        return results

    # 并发处理所有查询条件
    tasks = [process_search_args(args) for args in search_args]
    results = await asyncio.gather(*tasks)
    
    # 合并所有结果
    for res in results:
        all_results.extend(res)
    
    return all_results