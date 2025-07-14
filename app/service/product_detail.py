import httpx
from urllib.parse import urlencode
from utils.config import config
from utils.log import log
import traceback
from service.product_feature_search import get_feature_desc
from dashscope.aigc.generation import AioGeneration
from utils.security import decrypt
from typing import List

api_key = decrypt(config['api_key'])


async def get_product_info(product_num: str) -> dict:
    """
    异步获取产品信息

    Args:
        product_num: 产品编号

    Returns:
        产品信息字典 (API返回的data字段)
        失败时返回空字典
    """
    # 构造请求URL（实际场景中UAT和PROD的域名可能不同）
    base_url = config["uux_base_url"]
    url = f"{base_url}/productInfo?{urlencode({'productNum': product_num})}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json().get('data', {})
    except httpx.HTTPStatusError as e:
        log.error(f"产品查询失败: {str(e)}, URL: {url}, 状态码: {e.response.status_code}")
    except httpx.RequestError as e:
        log.error(f"请求失败: {str(e)}, URL: {url}")
    except Exception as e:
        log.error(f"系统异常: {str(e)}")
        trace_info = traceback.format_exc()
        log.error(f"异常详情: {trace_info}")

    return {}  # 失败时返回空字典


async def parse_product_info(product_infos: List[dict], demand: str) -> str:
    """
    使用大模型根据需求从产品信息中提取特定内容

    Args:
        product_infos: 产品信息列表
        demand: 提取需求描述

    Returns:
        根据需求提取的信息
    """
    # 首先收集所有产品的基本信息文本
    product_texts = []

    for product_info in product_infos:
        if not product_info:
            continue

        product_num = product_info.get('productNum', '未知编号')
        product_text = f"【产品编号: {product_num}】\n"

        line_list = product_info.get("lineList", [])
        for line in line_list:
            # 交通信息
            traffic_info = line.get('goTransportName', '') + " " + line.get('backTransportName', '')
            if traffic_info.strip():
                product_text += f"交通: {traffic_info}\n"

            # 航班信息
            for flight_type in ['goAirports', 'backAirports']:
                flights = line.get(flight_type, [])
                for flight in flights:
                    product_text += f"航班: {flight.get('airlineName', '')} {flight.get('flightNo', '')} " \
                                    f"{flight.get('startAirportName', '')}->{flight.get('arriveAirportName', '')}\n"

            # 每日行程
            for trip in line.get("trips", []):
                product_text += f"\n第{trip.get('dayNum', '')}天: {trip.get('content', '')}\n"

                # 景点
                for spot in trip.get('scenicSpots', []):
                    product_text += f"景点: {spot.get('name', '')} ({spot.get('city', '未知城市')}) - {spot.get('description', '')}\n"

                # 酒店
                for hotel in trip.get('hotels', []):
                    product_text += f"酒店: {hotel.get('name', '')} ({hotel.get('star', '')}星) - {hotel.get('address', '')}\n"

                # 购物
                for store in trip.get('stores', []):
                    product_text += f"购物: {store.get('name', '')} - {store.get('mainProducts', '')}\n"

        product_texts.append(product_text)

    # 准备给大模型的提示
    full_text = "\n\n".join(product_texts)
    prompt = f"""
    请根据以下用户需求从产品信息中提取相关内容：
    用户需求：{demand}

    产品信息：
    {full_text}

    要求：
    1. 只返回与需求直接相关的信息
    2. 保持信息的原始内容，不要修改或总结
    3. 请注明产品编号
    """

    # 调用大模型处理
    response = await AioGeneration.call(
        model='qwen-plus',
        prompt=prompt,
        result_format='message',
        temperature=0,
        api_key=api_key
    )

    return response['output']['choices'][0]['message']['content']
