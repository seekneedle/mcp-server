from service.retrieve_needle import retrieve_needle
from utils.config import config
from utils.security import decrypt
from utils.log import log
import os
from urllib.parse import unquote
import aiohttp
import asyncio
from typing import List, Dict, Any

CLIENT_SECRET = decrypt(config["vision_client_secret"])
CLIENT_PASSWORD = decrypt(config["vision_password"])

async def download_image(session: aiohttp.ClientSession, url: str, file_name: str = None, save_dir: str = 'downloads') -> str:
    """
    下载图片并保存到本地

    :param session: aiohttp ClientSession
    :param url: 图片下载URL
    :param file_name: 自定义文件名（可选）
    :param save_dir: 保存目录，默认为'downloads'
    :return: 保存的文件路径
    """
    # 创建保存目录（如果不存在）
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 获取响应内容
    async with session.get(url) as response:
        response.raise_for_status()  # 检查请求是否成功

        # 从URL或响应头中提取文件名
        if not file_name:
            # 尝试从Content-Disposition头获取文件名
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                file_name = content_disposition.split('filename=')[1].strip('"\'')
            else:
                # 从URL中提取文件名
                file_name = unquote(url.split('/')[-1].split('?')[0])

        # 确保文件名有正确的扩展名
        if not file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            file_name += '.jpg'  # 默认使用.jpg扩展名

        # 完整的文件保存路径
        file_path = os.path.join(save_dir, file_name)

        # 写入文件
        with open(file_path, 'wb') as f:
            while True:
                chunk = await response.content.read(1024)
                if not chunk:
                    break
                f.write(chunk)

        return file_path

async def search_vision(query: str, search_num: int = 1) -> List[str]:
    file_paths = []
    async with aiohttp.ClientSession() as session:
        # 第一个请求：获取access token
        token_url = "http://api.fotomore.com/api/oauth2/access_token"
        token_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/plain"
        }
        token_data = {
            "client_id": config["vision_client_id"],
            "client_secret": CLIENT_SECRET,
            "username": config["vision_username"],
            "password": CLIENT_PASSWORD,
            "grant_type": config["vision_grant_type"]
        }

        # 发送请求获取token
        async with session.post(token_url, headers=token_headers, data=token_data) as token_response:
            if token_response.status == 200:
                # 假设响应是JSON格式，包含access_token
                token_json = await token_response.json()
                access_token = token_json.get("access_token")
                log.info(f"成功获取access token: {access_token}")

                # 第二个请求：使用获取的token访问API
                search_url = f"http://api.fotomore.com/api/purchase/search?keywords={query}&page=1&nums={search_num}"
                search_headers = {
                    "Accept": "text/html",
                    "api-key": config["vision_client_id"],
                    "authorization": f"Bearer {access_token}"
                }

                async with session.get(search_url, headers=search_headers) as search_response:
                    if search_response.status == 200:
                        search_json = await search_response.json()
                        log.info(f"成功获取图片数据: {search_json}")
                        images = search_json["data"]["list"]
                        for item in images:
                            if 'down_url' in item:
                                log.info(f"开始下载图片 {item['id']}...")
                                try:
                                    # 使用图片ID作为文件名前缀
                                    saved_path = await download_image(
                                        session,
                                        item['down_url'],
                                        file_name=f"{item['id']}_{item.get('title', 'image')}.jpg"
                                    )
                                    file_paths.append(saved_path)
                                    log.info(f"图片已保存到: {saved_path}")
                                except Exception as e:
                                    log.error(f"下载图片失败: {e}")
                            else:
                                log.warning(f"图片主题: {item['title']} 没有下载链接")
                    else:
                        log.error(f"搜索图片失败，状态码: {search_response.status}")
                        log.error(await search_response.text())
            else:
                log.error(f"获取access token失败，状态码: {token_response.status}")
                log.error(await token_response.text())

    return file_paths

async def image_search(query: str) -> List[str]:
    results = retrieve_needle(query, index_id=config["image_id"])
    all_results = []
    for result in results:
        all_results.append(result["meta"]["file_name"])
    if len(results) < 3:
        vision_results = await search_vision(query, 3 - len(results))
        all_results.extend(vision_results)
    return all_results

async def images_search(queries: List[str]) -> Dict[str, List[str]]:
    tasks = [image_search(query) for query in queries]
    results = await asyncio.gather(*tasks)

    all_results = {}
    # 合并所有结果
    for query, res in zip(queries, results):
        all_results[query] = res

    return all_results