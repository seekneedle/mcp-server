from service.retrieve_needle import retrieve_needle
from utils.config import config
import asyncio
from typing import List, Dict
import concurrent.futures

# 创建线程池执行器用于后台任务
executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

KB_ID = config["image_id"]

async def image_search(query: str, image_num) -> List[str]:
    results = await retrieve_needle(query, index_id=KB_ID, top_k=image_num)
    all_results = []
    for result in results:
        file_name = result["metadata"]["doc_name"]
        split_names = file_name.split(".")[0].split("_")
        title = split_names[0]
        extension = split_names[-1]
        file_name = title + '.' + extension
        link = f"{config['oss_link']}{file_name}"
        all_results.append(link)
    return all_results

async def images_search(queries: List[str], image_num: int) -> Dict[str, List[str]]:
    tasks = [image_search(query, image_num) for query in queries]
    results = await asyncio.gather(*tasks)

    all_results = {}
    # 合并所有结果
    for query, res in zip(queries, results):
        all_results[query] = res

    return all_results