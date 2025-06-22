from utils.config import config
from utils.security import decrypt
import aiohttp
from utils.log import log

URL = config["needle_base_url"]
ID = config["needle_id"]
AUTH = decrypt(config["needle_auth"])

HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': AUTH
}

async def retrieve_needle(query: str, top_k: int):
    data = {
        "id": ID,  # 确保ID已定义
        "query": query,
        "min_score": 0,
        "rerank_top_k": top_k,
        "top_k": top_k * 5,
        "sparse_top_k": top_k * 5
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                    URL,
                    headers=HEADERS,
                    json=data
            ) as response:

                response.raise_for_status()  # 检查HTTP状态码
                result = await response.json()

                product_nums = [
                    chunk['metadata']['doc_name']
                    for chunk in result['data']['chunks']
                ]
                log.info(f"retrieve_needle query: {query}, product_nums: {product_nums}")
                return product_nums

        except aiohttp.ClientError as e:
            log.error(f"retrieve_needle HTTP请求失败: {e}")
            return []
        except KeyError as e:
            log.error(f"retrieve_needle 响应数据格式异常: {e}")
            return []
        except Exception as e:
            log.error(f"retrieve_needle 未知错误: {e}")
            return []