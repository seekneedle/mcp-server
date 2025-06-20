from typing import List
from service.product_search import product_search

async def search_product_nums(product_nums: List[str]):
    if not product_nums:
        return ''

    search_args = [{"productNum": num} for num in product_nums]

    # 调用product_search进行批量查询
    results = await product_search(search_args)

    return results