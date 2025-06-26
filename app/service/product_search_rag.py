from service.retrieve_needle import retrieve_needle
from service.product_feature_search import product_feature_search


async def search_rag(query: str, top_k: int):
    product_nums = await retrieve_needle(query, top_k)
    if not product_nums:
        return ''

    search_args = [{"productNum": num} for num in product_nums]

    # 调用product_search进行批量查询
    results = await product_feature_search(search_args)

    return results
