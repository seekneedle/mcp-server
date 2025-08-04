from typing import Dict, Optional
import httpx
from utils.config import config
from utils.log import log
from urllib.parse import urlencode
from utils.geo import get_city_code, get_province_code, get_country_code
from utils.security import decrypt
import traceback
from dashscope.aigc.generation import AioGeneration
from http import HTTPStatus
import json

api_key = decrypt(config['api_key'])


class PageResult(object):
    def __init__(self, current_page: int, total_pages: int, message: str):
        self.current_page = current_page
        self.total_pages = total_pages
        self.message = message
        self.result = f"当前页：{self.current_page}\n总页数：{self.total_pages}\n旅行产品信息：\n{self.message}"


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
        async with httpx.AsyncClient(timeout=config['timeout']) as client:
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
        async with httpx.AsyncClient(timeout=config['timeout']) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json().get('data')
    except Exception as e:
        log.error(f"获取产品详情失败: {str(e)}, productNum: {product_num}")
        return None


async def get_scenics(content) -> str:
    try:
        # 调用百炼平台API（启用内置JSON模式）
        response = await AioGeneration.call(
            model='qwen-max',
            prompt=f"""
            已知信息：
            {content}
            
            从已知信息中提取城市景点的名称，要求只需要提取城市和该城市包含的景点的名称。
            """,
            result_format='message',
            temperature=0,
            api_key=api_key
        )

        if response.status_code == HTTPStatus.OK:
            # 直接获取平台解析好的JSON
            result_str = response.output.choices[0].message.content
            log.info(f"get_scenics 解析结果：{result_str}")
            return result_str
        else:
            return "景点信息提取失败。"

    except Exception as e:
        log.error(f"get_scenics 解析失败: {str(e)}", exc_info=True)
        return "未找到城市和景点信息"

async def get_product_abs(product_num: str) -> str:
    """获取单个产品的特征描述（仅包含行程信息和往返航班）"""
    product_detail = await fetch_product_detail(product_num)
    if not product_detail:
        return f"产品 {product_num} 框架获取失败"

    product_features = []

    if "lineList" in product_detail and product_detail["lineList"]:
        line = product_detail["lineList"][0]  # 只处理第一条线路

        # 行程信息（严格保持原有遍历方式）
        if "trips" in line and line["trips"]:
            product_features.append(f"产品编号：{product_num}")
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
                    #product_features.append(get_feature_desc(trip, "行程内容", 'content'))
                    content = get_feature_desc(trip, "行程内容", 'content')
                    scenics = await get_scenics(content)
                    product_features.append(scenics)

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
            product_features.append(f"产品编号：{product_num}")
            # 往返航班信息（严格保持原有获取方式）
            product_features.append("=== 往返航班信息 ===")
            if line['calList']:
                cal = line['calList'][0]
                product_features.append(f"成年人售价：{cal['adultSalePrice']}")
                product_features.append(f"儿童售价：{cal['childSalePrice']}")
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


#################################################################################################################################


async def search_params_abs(search_args, current_page) -> PageResult:
    if not search_args:
        return PageResult(current_page, 0, "旅行产品框架：至少需要提供国家、省份或城市中的一个参数")

    # 设置分页参数
    params = {
        "current": current_page,
        "pageSize": 10,
        **search_args
    }

    try:
        response = await fetch_product_page(params)
        if not response or 'data' not in response:
            return PageResult(current_page, 0, "旅行产品框架：未获取到有效数据")

        data = response['data']
        total_pages = int(data.get('pages', 1))
        products = data.get('records', [])

        if current_page > total_pages:
            return PageResult(current_page, total_pages, "超过总页数范围")

        # 获取所有产品的框架信息
        product_features = []
        cnt = 0
        for product in products:
            if product_num := product.get('productNum'):
                features = await get_product_abs(product_num)
                if features:
                    cnt += 1
                    product_features.append(features)
                    if cnt >2:
                        break

        if not product_features:
            return PageResult(current_page, total_pages, "本页未找到有效产品，请查询其他页")

        message = "查询成功\n" + "\n\n".join(product_features)

        log.info(f"【产品检索长度】【{search_args}】: {len(message)}")

        return PageResult(current_page, total_pages, f"旅行产品框架：\n{message}")

    except Exception as e:
        log.error(f"目的地产品查询失败: {str(e)}")
        return PageResult(current_page, 0, f"旅行产品框架：查询失败: {str(e)}")


async def search_by_destination_abs(country: str = "", province: str = "", city: str = "", current_page: int = 1) -> PageResult:
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

    page_result = await search_params_abs(search_args, current_page)
    return page_result



async def search_by_pass_through_abs(country: str = "", province: str = "", city: str = "", current_page: int = 1) -> PageResult:
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

    page_result = await search_params_abs(search_args, current_page)
    return page_result


async def search_by_abs(country: str = "", province: str = "", city: str = "", current_page: int = 1) -> str:
    page_result = await search_by_destination_abs(country, province, city, current_page)
    if current_page <= page_result.total_pages:
        return f"当前页：{current_page}\n总页数：{page_result.total_pages}\n旅行产品信息：\n{page_result.message}"
    pass_current_page = current_page - page_result.total_pages
    pass_page_result = await search_by_pass_through_abs(country, province, city, pass_current_page)
    pass_total_pages = page_result.total_pages + pass_page_result.total_pages
    if pass_current_page <= pass_page_result.total_pages:
        return f"当前页：{current_page}\n总页数：{pass_total_pages}\n旅行产品信息：\n{pass_page_result.message}"
    return f"当前页：{current_page}\n总页数：{pass_total_pages}\n旅行产品信息：\n{pass_page_result.message}"



#################################################################################################################################



async def search_params_detail(search_args, current_page) -> PageResult:
    if not search_args:
        return PageResult(current_page, 0, "旅行产品信息：至少需要提供国家、省份或城市中的一个参数")

    # 设置分页参数
    params = {
        "current": current_page,
        "pageSize": 10,
        **search_args
    }

    try:
        response = await fetch_product_page(params)
        if not response or 'data' not in response:
            return PageResult(current_page, 0, "旅行产品信息：未获取到有效数据")

        data = response['data']
        total_pages = int(data.get('pages', 1))
        products = data.get('records', [])

        if current_page > total_pages:
            return PageResult(current_page, total_pages, "超过总页数范围")

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

        if not product_features:
            return PageResult(current_page, total_pages, "本页未找到有效产品信息，请查询其他页")

        message = "查询成功\n" + "\n\n".join(product_features)

        log.info(f"【产品检索长度】【{search_args}】: {len(message)}")

        return PageResult(current_page, total_pages, f"旅行产品信息：\n{message}")

    except Exception as e:
        log.error(f"目的地产品查询失败: {str(e)}")
        return PageResult(current_page, 0, f"旅行产品信息：查询失败: {str(e)}")


async def search_by_destination(country: str = "", province: str = "", city: str = "", current_page: int = 1) -> PageResult:
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

    page_result = await search_params_detail(search_args, current_page)
    return page_result



async def search_by_pass_through(country: str = "", province: str = "", city: str = "", current_page: int = 1) -> PageResult:
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

    page_result = await search_params_detail(search_args, current_page)
    return page_result


async def search_by_detail(country: str = "", province: str = "", city: str = "", current_page: int = 1) -> str:
    page_result = await search_by_destination(country, province, city, current_page)
    if current_page <= page_result.total_pages:
        return f"当前页：{current_page}\n总页数：{page_result.total_pages}\n旅行产品信息：\n{page_result.message}"
    pass_current_page = current_page - page_result.total_pages
    pass_page_result = await search_by_pass_through(country, province, city, pass_current_page)
    pass_total_pages = page_result.total_pages + pass_page_result.total_pages
    if pass_current_page <= pass_page_result.total_pages:
        return f"当前页：{current_page}\n总页数：{pass_total_pages}\n旅行产品信息：\n{pass_page_result.message}"
    return f"当前页：{current_page}\n总页数：{pass_total_pages}\n旅行产品信息：\n{pass_page_result.message}"