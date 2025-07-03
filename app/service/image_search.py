from service.retrieve_needle import retrieve_needle
from utils.config import config
from utils.security import decrypt
from utils.log import log
import os
from urllib.parse import unquote
import aiohttp
import asyncio
from typing import List, Dict
from aiohttp import FormData
import alibabacloud_oss_v2 as oss
import traceback

# 从 config 中读取 OSS 相关配置，并设置环境变量
os.environ["OSS_ACCESS_KEY_ID"] = config["oss_access_key_id"]
os.environ["OSS_ACCESS_KEY_SECRET"] = decrypt(config["oss_access_key_secret"])  # 如果有加密，先解

IMAGE_URL = config["vision_url"]
CLIENT_ID = config["vision_client_id"]
SECRET = decrypt(config["vision_client_secret"])
USERNAME = config["vision_username"]
PASSWORD = decrypt(config["vision_password"])
TYPE = config["vision_grant_type"]
KB_ID = config["image_id"]
ADD_URL = config["needle_base_url"] + "/vector_store/file/add"
AUTH = decrypt(config["needle_auth"])

TEMP_PATH = os.path.join(os.path.dirname(__file__), '..', '..', config['data_dir'], 'image')
if not os.path.exists(TEMP_PATH):
    os.makedirs(TEMP_PATH)

async def download_image(session: aiohttp.ClientSession, url: str, file_name: str = None, save_dir: str = TEMP_PATH) -> str:
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


async def save_kb(file_name: str, file_content: str) -> None:
    url = ADD_URL  # 替换为实际URL
    auth = AUTH  # 替换为实际认证信息
    kb_id = KB_ID  # 替换为知识库ID

    # 准备表单数据
    form = FormData()
    form.add_field("id", kb_id)
    form.add_field(
        "files",
        file_content.encode('utf-8'),
        filename=file_name,
        content_type="application/octet-stream"
    )

    headers = {"Authorization": auth}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    url,
                    headers=headers,
                    data=form
            ) as response:
                response.raise_for_status()  # 检查HTTP错误
                result = await response.text()
                log.info(f"Saved {file_name} to KB. Response: {result}")

    except aiohttp.ClientError as e:
        trace_info = traceback.format_exc()
        log.error(f"Failed to save {file_name}: {str(e)}, trace: {trace_info}")
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"Unexpected error saving {file_name}: {str(e)}, trace: {trace_info}")


# 全局 OSS 客户端变量（改为异步安全的初始化方式）
oss_client = None
oss_lock = asyncio.Lock()  # 添加异步锁确保线程安全


async def init_oss_client():
    """
    异步初始化OSS客户端（从配置读取参数）
    """
    global oss_client

    async with oss_lock:
        if oss_client is not None:
            return

        # 从环境变量中加载凭证信息，用于身份验证
        credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()

        # 加载SDK的默认配置，并设置凭证提供者
        cfg = oss.config.load_default()
        cfg.credentials_provider = credentials_provider

        # 设置配置中的区域信息
        cfg.region = config["oss_region"]

        # 初始化OSS客户端和存储桶
        try:
            oss_client = oss.Client(cfg)
            log.info("OSS client initialized successfully")
        except Exception as e:
            trace_info = traceback.format_exc()
            log.error(f"Failed to initialize OSS client: {str(e)}, trace: {trace_info}")
            raise


async def save_oss(jpg_path: str) -> str:
    """
    异步上传文件到OSS，生成唯一object key
    :param jpg_path: 本地文件路径
    :return: OSS object key
    """
    # 确保客户端已初始化
    if oss_client is None:
        await init_oss_client()

    # 生成唯一object key（使用UUID + 原始文件名）
    file_name = os.path.basename(jpg_path)
    object_key = file_name

    try:
        # 使用异步方式上传文件
        result = oss_client.put_object_from_file(
            oss.PutObjectRequest(
                bucket=config["oss_bucket"],
                key=object_key
            ),
            jpg_path
        )
        log.info(f"OSS upload result: {jpg_path} -> {object_key}: {result}")
        return object_key
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"OSS upload failed: {str(e)}, trace: {trace_info}")
        raise


async def search_vision(query: str, search_num: int = 1) -> List[str]:
    file_paths = []
    async with aiohttp.ClientSession() as session:
        # 第一个请求：获取access token
        token_url = f"{IMAGE_URL}/api/oauth2/access_token"
        token_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/plain"
        }
        token_data = {
            "client_id": CLIENT_ID,
            "client_secret": SECRET,
            "username": USERNAME,
            "password": PASSWORD,
            "grant_type": TYPE
        }

        # 发送请求获取token
        async with session.post(token_url, headers=token_headers, data=token_data) as token_response:
            if token_response.status == 200:
                # 假设响应是JSON格式，包含access_token
                token_json = await token_response.json()
                access_token = token_json.get("access_token")
                log.info(f"成功获取access token: {access_token}")

                # 第二个请求：使用获取的token访问API
                search_url = f"{IMAGE_URL}/api/purchase/search?keywords={query}&page=1&nums={search_num}"
                search_headers = {
                    "Accept": "text/html",
                    "api-key": CLIENT_ID,
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
                                        file_name=f"{item.get('title', 'image')}.jpg"
                                    )
                                    await save_oss(saved_path)
                                    await save_kb(item.get('title', 'image'), f"{item['id']}_{item.get('title', 'image')}.jpg\n{query}")
                                    file_paths.append(saved_path)
                                    log.info(f"图片已保存到: {saved_path}")
                                except Exception as e:
                                    trace_info = traceback.format_exc()
                                    log.error(f"下载图片失败: {e}, trace: {trace_info}")
                            else:
                                log.warning(f"图片主题: {item['title']} 没有下载链接")
                    else:
                        log.error(f"搜索图片失败，状态码: {search_response.status}")
                        log.error(await search_response.text())
            else:
                log.error(f"获取access token失败，状态码: {token_response.status}")
                log.error(await token_response.text())

    return file_paths

async def image_search(query: str, image_num) -> List[str]:
    results = await retrieve_needle(query, index_id=KB_ID)
    all_results = []
    for result in results:
        all_results.append(result["meta"]["file_name"])
    if len(results) < image_num:
        vision_results = await search_vision(query, 3 - len(results))
        all_results.extend(vision_results)
    return all_results

async def images_search(queries: List[str], image_num: int) -> Dict[str, List[str]]:
    tasks = [image_search(query, image_num) for query in queries]
    results = await asyncio.gather(*tasks)

    all_results = {}
    # 合并所有结果
    for query, res in zip(queries, results):
        all_results[query] = res

    return all_results