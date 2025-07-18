from typing import Dict, Optional
import httpx
from utils.config import config
from utils.log import log
from urllib.parse import urlencode
from utils.geo import get_city_code, get_province_code, get_country_code
import json
import traceback


def get_feature_desc(product_detail, intro, parent_key, keys=None):
    """获取产品特征描述"""
    if not product_detail or not parent_key:
        return ""

    try:
        values = []

        if keys is None:
            key_list = parent_key.split(".")
            current_dict = product_detail

            for k in key_list[:-1]:
                current_dict = current_dict.get(k)
                if current_dict is None:
                    return f"{intro}："

            if current_dict is not None:
                last_key = key_list[-1]
                if isinstance(current_dict, list):
                    for child_dict in current_dict:
                        values.append(str(child_dict.get(last_key, "")))
                else:
                    value_str = str(current_dict.get(last_key, ""))
                    values.append(value_str)

        else:
            key_list = parent_key.split(".")
            current_dict = product_detail

            for k in key_list:
                current_dict = current_dict.get(k)
                if current_dict is None:
                    return f"{intro}："

            if current_dict is not None:
                if isinstance(current_dict, list):
                    for child_dict in current_dict:
                        child_values = []
                        for key in keys:
                            value = child_dict.get(key, "")
                            if value is not None and str(value) != "null":
                                update_value = str(value).replace("\n", " ")
                                child_values.append(update_value)
                        values.append("、".join(child_values))
                elif isinstance(current_dict, dict):
                    child_values = []
                    for key in keys:
                        value = current_dict.get(key, "")
                        if value is not None and str(value) != "null":
                            update_value = str(value).replace("\n", " ")
                            child_values.append(update_value)
                    values.append("、".join(child_values))

        combined_value = "; ".join(values)
        return f"{intro}：{combined_value}"

    except Exception:
        return f"{intro}："


async def fetch_product_page(params: Dict) -> Optional[Dict]:
    """获取单页数据"""
    base_url = config['uux_base_url']
    url = f"{base_url}/page?{urlencode(params)}"
    log.info(f"Fetching data from: {url}")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.error(f"查询失败: {str(e)}, params: {params}")
        return None


async def fetch_product_detail(product_num: str) -> Optional[Dict]:
    """获取单个产品详细信息"""
    base_url = config['uux_base_url']
    url = f"{base_url}/productInfo?productNum={product_num}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json().get('data')
    except Exception as e:
        log.error(f"获取产品详情失败: {str(e)}, productNum: {product_num}")
        return None


async def get_product_features(product_num: str) -> str:
    """获取单个产品的特征描述（仅包含行程信息和往返航班）"""
    product_detail = await fetch_product_detail(product_num)
    if not product_detail:
        return f"产品 {product_num} 详情获取失败"

    product_features = []

    if "lineList" in product_detail and product_detail["lineList"]:
        line = product_detail["lineList"][0]  # 只处理第一条线路

        # 行程信息（严格保持原有遍历方式）
        if "trips" in line and line["trips"]:
            # 往返航班信息（严格保持原有获取方式）
            product_features.append("=== 往返航班信息 ===")
            product_features.append(get_feature_desc(line, "去程交通", 'goTransportName'))
            product_features.append(get_feature_desc(line,
                                                     "去程航班（航空公司、航班号、出发机场、到达机场、出发时间、到达时间）",
                                                     'goAirports', ["airlineName", "flightNo", "startAirportName",
                                                                    "arriveAirportName", "startTime", "arriveTime"]))
            product_features.append(get_feature_desc(line, "回程交通", 'backTransportName'))
            product_features.append(get_feature_desc(line,
                                                     "回程航班（航空公司、航班号、出发机场、到达机场、出发时间、到达时间）",
                                                     'backAirports', ["airlineName", "flightNo", "startAirportName",
                                                                      "arriveAirportName", "startTime", "arriveTime"]))

            product_features.append("\n=== 每日行程信息 ===")
            try:
                for trip in line["trips"]:
                    product_features.append(f"\n【第 {trip.get('tripDay', '?')} 天】")
                    product_features.append(get_feature_desc(trip, "行程内容", 'content'))

                    # 保持原有交通信息获取方式
                    product_features.append(get_feature_desc(trip,
                                                             "交通（出发地、时间、目的地、到达时间、方式）",
                                                             'scheduleTraffics',
                                                             ["departure", "departureTime", "destination",
                                                              "arrivalTime", "trafficType"]))

                    # 保持原有酒店信息获取方式
                    product_features.append(get_feature_desc(trip,
                                                             "酒店（名称、星级）",
                                                             'hotels', ["name", "star"]))

                    # 保持原有景点信息获取方式
                    product_features.append(get_feature_desc(trip,
                                                             "景点（名称、描述）",
                                                             'scenics', ["name", "description"]))

            except Exception as e:
                trace_info = traceback.format_exc()
                log.error(f'获取行程信息异常: {str(e)}\n{trace_info}')
                product_features.append("行程信息获取异常")

    return "\n".join([f for f in product_features if f and not f.endswith("：")])


async def search_by_destination(country: str = "", province: str = "", city: str = "", current_page: int = 1) -> str:
    """
    根据目的地查询产品信息

    Args:
        country: 国家名称
        province: 省份名称
        city: 城市名称
        current_page: 当前页码

    Returns:
        文字格式:
        当前页：。。。
        总页数：。。。
        旅行产品信息：。。。
    """
    # 构建查询参数
    search_args = {}
    if country and get_country_code(country):
        search_args["destCountryCode"] = get_country_code(country)
    if province and get_province_code(province):
        search_args["destProvinceCode"] = get_province_code(province)
    if city and get_city_code(city):
        search_args["destCityCode"] = get_city_code(city)

    if not search_args:
        return "当前页：1\n总页数：1\n旅行产品信息：至少需要提供国家、省份或城市中的一个参数"

    # 设置分页参数
    params = {
        "current": current_page,
        "pageSize": 10,
        **search_args
    }

    try:
        response = await fetch_product_page(params)
        if not response or 'data' not in response:
            return f"当前页：{current_page}\n总页数：1\n旅行产品信息：未获取到有效数据"

        data = response['data']
        total_pages = data.get('pages', 1)
        products = data.get('records', [])

        # 获取所有产品的详细信息
        product_features = []
        cnt = 0
        for product in products:
            if product_num := product.get('productNum'):
                features = await get_product_features(product_num)
                if features:
                    cnt += 1
                    product_features.append(features)
                    if cnt >2:
                        break

        message = "查询成功\n" + "\n\n".join(product_features) if product_features else "没有找到产品详细信息"

        log.info(f"【产品检索长度】【{search_args}】: {len(message)}")

        return f"当前页：{current_page}\n总页数：{total_pages}\n旅行产品信息：\n{message}"

    except Exception as e:
        log.error(f"目的地产品查询失败: {str(e)}")
        return f"当前页：{current_page}\n总页数：1\n旅行产品信息：查询失败: {str(e)}"


async def search_by_pass_through(country: str = "", province: str = "", city: str = "", current_page: int = 1) -> str:
    """
    根据途经地查询产品信息

    Args:
        country: 国家名称
        province: 省份名称
        city: 城市名称
        current_page: 当前页码

    Returns:
        文字格式:
        当前页：。。。
        总页数：。。。
        旅行产品信息：。。。
    """
    # 构建查询参数
    search_args = {}
    if country and get_country_code(country):
        search_args["passCountryCode"] = get_country_code(country)
    if province and get_province_code(province):
        search_args["passProvinceCode"] = get_province_code(province)
    if city and get_city_code(city):
        search_args["passCityCode"] = get_city_code(city)

    if not search_args:
        return "当前页：1\n总页数：1\n旅行产品信息：至少需要提供国家、省份或城市中的一个参数"

    # 设置分页参数
    params = {
        "current": current_page,
        "pageSize": 10,
        **search_args
    }

    try:
        response = await fetch_product_page(params)
        if not response or 'data' not in response:
            return f"当前页：{current_page}\n总页数：1\n旅行产品信息：未获取到有效数据"

        data = response['data']
        total_pages = data.get('pages', 1)
        products = data.get('records', [])

        # 获取所有产品的详细信息
        product_features = []
        for product in products:
            if product_num := product.get('productNum'):
                features = await get_product_features(product_num)
                product_features.append(features)

        message = "查询成功\n" + "\n\n".join(product_features) if product_features else "没有找到产品详细信息"

        return f"当前页：{current_page}\n总页数：{total_pages}\n旅行产品信息：\n{message}"

    except Exception as e:
        log.error(f"途经地产品查询失败: {str(e)}")
        return f"当前页：{current_page}\n总页数：1\n旅行产品信息：查询失败: {str(e)}"