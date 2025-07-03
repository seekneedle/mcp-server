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
        log.error(f"Failed to save {file_name}: {str(e)}")
    except Exception as e:
        log.error(f"Unexpected error saving {file_name}: {str(e)}")


# 全局OSS客户端变量
oss_client = None
oss_bucket = None


def init_oss_client(region, bucket, endpoint=None):
    """
    初始化全局OSS客户端
    :param region: OSS存储区域（如'oss-cn-hangzhou'）
    :param bucket: OSS存储桶名称
    :param endpoint: 自定义端点URL（可选）
    """
    global oss_client, oss_bucket

    # 从环境变量加载凭证（需设置ALIBABA_CLOUD_ACCESS_KEY_ID和ALIBABA_CLOUD_ACCESS_KEY_SECRET）
    credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()

    # 创建OSS配置
    cfg = oss.config.Config(
        credentials_provider=credentials_provider,
        region=region
    )

    # 设置自定义端点（如果提供）
    if endpoint:
        cfg.endpoint = endpoint

    # 初始化全局客户端和存储桶
    oss_client = oss.Client(cfg)
    oss_bucket = bucket


def save_oss(jpg_path):
    """
    上传JPG文件到预配置的OSS存储桶
    :param jpg_path: 本地JPG文件路径
    :return: 上传结果对象
    """
    if oss_client is None or oss_bucket is None:
        raise RuntimeError("OSS客户端未初始化，请先调用init_oss_client()")

    # 从文件路径提取文件名作为OSS对象名
    object_key = os.path.basename(jpg_path)

    # 执行文件上传
    result = oss_client.put_object_from_file(
        oss.PutObjectRequest(
            bucket=oss_bucket,
            key=object_key
        ),
        jpg_path
    )

    # 返回上传结果
    return result


# 初始化OSS客户端（只需执行一次）
init_oss_client(
    region='oss-cn-hangzhou',
    bucket='my-photo-bucket',
    endpoint='https://custom-endpoint.aliyuncs.com'  # 可选
)


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
    results = await retrieve_needle(query, index_id=KB_ID)
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