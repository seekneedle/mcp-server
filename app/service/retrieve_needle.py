from utils.config import config
from utils.security import decrypt
import httpx
from utils.log import log

URL = config["needle_base_url"] + "/vector_store/retrieve"
ID = config["needle_id"]
AUTH = decrypt(config["needle_auth"])

HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': AUTH
}


async def retrieve_needle(query: str, index_id: str = ID, top_k: int = 3, min_score: float = 0.3):
    data = {
        "id": index_id,
        "query": query,
        "min_score": min_score,
        "rerank_top_k": top_k,
        "top_k": top_k * 5,
        "sparse_top_k": top_k * 5
    }

    async with httpx.AsyncClient(timeout=config['timeout']) as client:
        try:
            response = await client.post(
                URL,
                headers=HEADERS,
                json=data
            )

            response.raise_for_status()  # 检查HTTP状态码
            result = response.json()

            log.info(f"retrieve_needle query: {query}, chunks: {result['data']['chunks']}")
            return result['data']['chunks']

        except httpx.HTTPStatusError as e:
            log.error(f"retrieve_needle HTTP请求失败: {e}")
            return []
        except KeyError as e:
            log.error(f"retrieve_needle 响应数据格式异常: {e}")
            return []
        except Exception as e:
            log.error(f"retrieve_needle 未知错误: {e}")
            return []