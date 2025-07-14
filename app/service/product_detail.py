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
    只处理每个产品的第一条线路(lineList[0])信息

    Args:
        product_infos: 产品信息列表
        demand: 提取需求描述

    Returns:
        根据需求提取的信息
    """
    product_texts = []

    for product_info in product_infos:
        if not product_info:
            continue

        product_num = product_info.get('productNum', '未知编号')
        product_text = ""

        try:
            # Get only the first line if exists
            line_list = product_info.get("lineList", [])
            if not line_list:
                continue

            line = line_list[0]  # Only use the first line
            log.info(f"产品 {product_num} 线路信息: {line}")

            # Collect product information
            product_details = []
            product_details.append(f"【产品信息】\n产品编号：{product_num}")

            # Process transportation info
            traffic_infos = []
            traffic_infos.append("【交通信息】")
            traffic_infos.append(get_feature_desc(line, "去程交通", 'goTransportName'))
            traffic_infos.append(get_feature_desc(line,
                                                  "去程航班（包括航空公司编码、航空公司名称、航班号、启程机场编码、去程机场名称、启程出发时间、到达机场编码、到达机场名称、到达时间、日期差、航班顺序）",
                                                  'goAirports',
                                                  ["airlineCode", "airlineName", "flightNo", "startAirportCode",
                                                   "startAirportName", "startTime", "arriveAirportCode",
                                                   "arriveAirportName", "arriveTime", "days", "flightSort"]))
            traffic_infos.append(get_feature_desc(line, "回程交通", 'backTransportName'))
            traffic_infos.append(get_feature_desc(line,
                                                  "回程航班（包括航空公司编码、航空公司名称、航班号、回程机场编码、回程机场名称、回程出发时间、到达机场编码、到达机场名称、到达时间、日期差、航班顺序）",
                                                  'backAirports',
                                                  ["airlineCode", "airlineName", "flightNo", "startAirportCode",
                                                   "startAirportName", "startTime", "arriveAirportCode",
                                                   "arriveAirportName", "arriveTime", "days", "flightSort"]))

            product_details.extend([info for info in traffic_infos if info])

            # Process daily trips from the first line only
            try:
                for trip in line.get("trips", []):
                    trip_infos = []
                    trip_infos.append(f"\n【第{trip.get('dayNum', '')}天行程】")

                    # 景点信息
                    scenic_spots = trip.get('scenicSpots', [])
                    if scenic_spots:
                        trip_infos.append("【景点信息】")
                        for spot in scenic_spots:
                            name = spot.get('name', '未知景点')
                            description = spot.get('description', '暂无描述')
                            trip_infos.append(f"{name}：{description}")

                    # 其他行程信息
                    trip_infos.append(get_feature_desc(trip, "行程内容描述", 'content'))
                    trip_infos.append(get_feature_desc(trip,
                                                       "当天交通信息（出发地、出发时间、目的地、到达时间、交通类型）",
                                                       'scheduleTraffics',
                                                       ["departure", "departureTime", "destination", "arrivalTime",
                                                        "trafficType"]))
                    trip_infos.append(get_feature_desc(trip, "酒店信息", 'hotels', ["name", "star"]))
                    trip_infos.append(get_feature_desc(trip, "特色商店", 'stores',
                                                       ["name", "mainProducts", "description"]))

                    product_details.extend([info for info in trip_infos if info])

            except Exception as e:
                trace_info = traceback.format_exc()
                log.error(f"产品 {product_num} 行程提取失败: {str(e)}, trace: {trace_info}")

            product_text = "\n".join(product_details)
            product_texts.append(product_text)

        except Exception as e:
            trace_info = traceback.format_exc()
            log.error(f"产品 {product_num} 信息提取失败: {str(e)}, trace: {trace_info}")
            continue

    # Prepare the prompt for LLM
    full_text = "\n\n".join(product_texts)
    prompt = f"""
    请根据以下用户需求从产品信息中筛选相关内容：
    用户需求：{demand}

    限制：
    1. 必须返回原文，不允许修改或总结
    2. 请注明产品编号来源

    产品信息：
    {full_text}
    """

    log.info(prompt)

    try:
        response = await AioGeneration.call(
            model='qwen-plus',
            prompt=prompt,
            result_format='message',
            temperature=0,
            api_key=api_key
        )
        parse_result = response['output']['choices'][0]['message']['content']
        log.info(f"解析结果： {parse_result}")
        return parse_result
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"大模型处理失败: {str(e)}, trace: {trace_info}")
        return "信息处理失败，请稍后再试"