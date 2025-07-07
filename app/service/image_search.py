from service.retrieve_needle import retrieve_needle
from utils.config import config
from utils.security import decrypt
from utils.log import log
import os
from urllib.parse import unquote
import aiohttp
import asyncio
from typing import List, Dict
import alibabacloud_oss_v2 as oss
import traceback
import concurrent.futures

# 创建线程池执行器用于后台任务
executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

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
    url = ADD_URL
    auth_header = AUTH
    kb_id = KB_ID

    # 创建表单数据
    form_data = aiohttp.FormData()
    form_data.add_field('id', kb_id)
    form_data.add_field(
        'files',
        file_content.encode('utf-8'),
        filename=file_name,
        content_type='text/plain'
    )

    headers = {
        "Authorization": auth_header
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data, headers=headers) as response:
                response_text = await response.text()
                status_code = response.status
                log.info(f"save kb result: status={status_code}, content={response_text}")
    except aiohttp.ClientError as e:
        trace_info = traceback.format_exc()
        log.error(f"HTTP request failed: {e}, trace: {trace_info}")


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


def sync_check_oss_exist(object_key: str) -> bool:
    """
    同步检查OSS中文件是否存在（在后台线程中执行）
    :param object_key: OSS对象键
    :return: 文件是否存在
    """
    global oss_client
    try:
        result = oss_client.is_object_exist(
            bucket=config["oss_bucket"],
            key=object_key,
        )
        log.info(f"OSS object exist check: {object_key}: {result}")
        return result
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"OSS exist check failed: {str(e)}, trace: {trace_info}")
        return False


async def check_oss_exist(file_name: str) -> bool:
    """
    异步检查OSS中文件是否存在
    :param file_name: 文件名
    :return: 文件是否存在
    """
    # 确保客户端已初始化
    if oss_client is None:
        await init_oss_client()
    
    object_key = config["oss_path"] + file_name
    
    # 在后台线程中执行同步的OSS检查操作
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, sync_check_oss_exist, object_key)


def sync_save_oss(jpg_path: str) -> None:
    """
    同步上传文件到OSS（在后台线程中执行）
    :param jpg_path: 本地文件路径
    """
    global oss_client
    
    file_name = os.path.basename(jpg_path)
    object_key = config["oss_path"] + file_name

    try:
        result = oss_client.put_object_from_file(
            oss.PutObjectRequest(
                bucket=config["oss_bucket"],
                key=object_key
            ),
            jpg_path
        )
        log.info(f"OSS upload result: {object_key}: {result}")
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"OSS upload failed: {str(e)}, trace: {trace_info}")


async def save_oss(jpg_path: str) -> None:
    """
    异步封装OSS上传操作
    :param jpg_path: 本地文件路径
    """
    # 确保客户端已初始化
    if oss_client is None:
        await init_oss_client()
    
    # 在后台线程中执行同步的OSS上传操作
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, sync_save_oss, jpg_path)


async def search_vision(query: str, search_num: int = 1) -> List[str]:
    log.info(f"检索vision, query: {query}, search_num: {search_num}")
    links = []
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
                search_url = f"{IMAGE_URL}/api/purchase/search?keywords={query}&page=1&asset_type=1&publish_times=2"
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
                            if 'down_url' in item and item['down_url'] != '':
                                # 使用图片title作为文件名
                                file_name = f"{item['title']}.{item['asset_format']}"
                                
                                # 检查图片是否已在OSS中存在
                                exists = await check_oss_exist(file_name)
                                if not exists:
                                    log.info(f"开始下载新图片 {item['title']}...")
                                    try:
                                        saved_path = await download_image(
                                            session,
                                            item['down_url'],
                                            file_name=file_name
                                        )
                                        await save_oss(saved_path)
                                        await save_kb(f"{item['title']}.txt", f"{file_name}###{query}")
                                        link = f"{config['oss_link']}{file_name}"
                                        links.append(link)
                                        log.info(f"图片已上传到OSS: {saved_path}")
                                        
                                        if len(links) >= search_num:
                                            break
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

    return links

async def image_search(query: str, image_num) -> List[str]:
    results = await retrieve_needle(query, index_id=KB_ID)
    all_results = []
    for result in results:
        text = result['text']
        file_name = text.split('###')[0]
        if file_name is not None and file_name != '':
            link = f"{config['oss_link']}{file_name}"
            all_results.append(link)
    if len(results) < image_num:
        vision_results = await search_vision(query, image_num - len(all_results))
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