import httpx
from urllib.parse import urlencode
from utils.config import config
from utils.log import log
import traceback
from service.product_feature_search import get_feature_desc
from dashscope.aigc.generation import AioGeneration
from utils.security import decrypt

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


async def parse_product_info(product_infos, demand):
    results = []

    # Enhanced system prompt for information extraction
    extraction_prompt_template = """
    请严格按照以下要求提取和整理旅行产品信息（产品编号：{product_num}）：

    1. 信息提取要求：
    - 必须包含产品编号：{product_num}
    - 景点介绍、购物店介绍必须一字不差地原样保留
    - 交通信息需要完整提取（包括航班号、时间、机场等所有细节）
    - 酒店信息需要包含名称和星级
    - 每天的行程安排需要清晰呈现

    2. 格式要求：
    - 对于缺失但重要的信息，请根据上下文合理补充并标注[补充]
    - 保持原始数据的准确性，不要修改原始描述
    - 使用清晰的标题分隔不同部分（如【产品信息】、【交通信息】、【每日行程】等）

    3. 特别注意事项：
    - 如果原始数据中有明显遗漏但根据行程逻辑应该存在的信息，请添加[注意：可能需要补充XX信息]
    - 购物店信息必须包含名称、特色产品和完整介绍
    - 景点描述必须完全保留原始文本

    请整理以下产品信息：
    """

    for product_info in product_infos:
        if not product_info:
            continue

        product_num = product_info.get('productNum', '未知编号')
        try:
            # Get only the first line if exists
            line_list = product_info.get("lineList", [])
            if not line_list:
                continue

            line = line_list[0]  # Only use the first line
            log.info(f"产品 {product_num} 线路信息: {line}")

            # Collect all information for this product
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
                    trip_infos.append("【每日行程】")
                    trip_infos.append(get_feature_desc(trip, "行程内容描述", 'content'))
                    trip_infos.append(get_feature_desc(trip,
                                                       "当天交通信息（出发地、出发时间、目的地、到达时间、交通类型）",
                                                       'scheduleTraffics',
                                                       ["departure", "departureTime", "destination", "arrivalTime",
                                                        "trafficType"]))
                    trip_infos.append(
                        get_feature_desc(trip, "酒店信息", 'hotels', ["name", "star"]))
                    trip_infos.append(get_feature_desc(trip, "特色商店", 'stores',
                                                       ["name", "mainProducts", "description"]))

                    product_details.extend([info for info in trip_infos if info])

            except Exception as e:
                trace_info = traceback.format_exc()
                log.error(f"产品 {product_num} 行程提取失败: {str(e)}, trace: {trace_info}")

            # Process all product info with a single LLM call
            product_info_text = "\n".join(product_details)
            prompt = extraction_prompt_template.format(product_num=product_num) + product_info_text

            response = await AioGeneration.call(
                model='qwen-max',
                prompt=prompt,
                result_format='message',
                temperature=0,
                api_key=api_key
            )

            processed_result = response['output']['choices'][0]['message']['content']
            results.append(processed_result)
            log.info(f"产品 {product_num} 处理结果: {processed_result}")

        except Exception as e:
            trace_info = traceback.format_exc()
            log.error(f"产品 {product_num} 信息提取失败: {str(e)}, trace: {trace_info}")

    return results