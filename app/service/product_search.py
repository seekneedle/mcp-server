from typing import List
from urllib.parse import urlencode
from utils.config import config
import aiohttp


def get_feature_desc(product_detail, intro, parent_key, keys=None):
    if not product_detail or not parent_key:
        return ""

    try:
        values = []

        if keys is None:
            key_list = parent_key.split(".")
            current_dict = product_detail

            # Navigate through the dictionary using keys in key_list
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

            # Navigate through the dictionary using keys in key_list
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

        # Join all values with ", "
        combined_value = "; ".join(values)
        return f"{intro}：{combined_value}"

    except Exception as e:
        print(f"An error occurred: {e}")
        return f"{intro}："


def build_url_with_params(params: dict) -> str:
    """
    将字典参数拼接到 URL 后面，形成完整的带查询参数的 URL

    Args:
        params (dict): 参数字典，如 {"key1": "value1", "key2": "value2"}

    Returns:
        str: 拼接后的完整 URL，如 "https://aaa.com?key1=value1&key2=value2"
    """
    query_string = urlencode(params)  # 将字典转换成查询字符串，如 "key1=value1&key2=value2"
    full_url = f"{config['uux_base_url']}?{query_string}"
    return full_url


async def search_one(arg):
    url = build_url_with_params(arg)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                product_detail = (await response.json())['data']
                product_features = [get_feature_desc(product_detail, "产品编号productNum", 'productNum'),
                                    get_feature_desc(product_detail, "参团游类型", 'productGroupTypeName'),
                                    get_feature_desc(product_detail, "参团游类型", 'productGroupTypeName'),
                                    get_feature_desc(product_detail, "产品类别", 'productTypeName'),
                                    get_feature_desc(product_detail, "产品名称", 'productTitle'),
                                    get_feature_desc(product_detail, "副标题", 'productSubtitle'),
                                    get_feature_desc(product_detail, "产品主题", 'themes.name'),
                                    get_feature_desc(product_detail, "目的地", 'dests',
                                                     ["continentName", "countryName", "destProvinceName",
                                                      "destCityName"]),
                                    get_feature_desc(product_detail, "产品标签", 'tags.name'),
                                    get_feature_desc(product_detail, "业务区域", 'businessAreas'),
                                    get_feature_desc(product_detail, "出发地国家", 'departureCountryName'),
                                    get_feature_desc(product_detail, "出发地省份", 'departureProvinceName'),
                                    get_feature_desc(product_detail, "出发地城市", 'departureCityName'),
                                    get_feature_desc(product_detail, "儿童年龄标准区间开始值", 'childAgeBegin'),
                                    get_feature_desc(product_detail, "儿童年龄标准区间结束值", 'childAgeEnd'),
                                    get_feature_desc(product_detail, "儿童身高标准区间开始值", 'childHeightBegin'),
                                    get_feature_desc(product_detail, "儿童身高标准区间结束值", 'childHeightEnd'),
                                    get_feature_desc(product_detail, "儿童价格是否含大交通", 'childHasTraffic'),
                                    get_feature_desc(product_detail, "儿童价是否含床", 'childHasBed'),
                                    get_feature_desc(product_detail, "儿童标准说明", 'childRule'),
                                    get_feature_desc(product_detail, "是否包含保险", 'insuranceIncluded'),
                                    get_feature_desc(product_detail, "营销标签", 'markets.name'),
                                    get_feature_desc(product_detail,
                                                     "保险名称、保险类型（境内外旅游险、航空险等）、保险内容", 'insurance',
                                                     ["name", "typeName", "content"])]
                try:
                    for i, line in enumerate(product_detail["lineList"]):
                        product_features.append(f"线路{i + 1}基本信息：")
                        product_features.append(get_feature_desc(line, "线路名称", 'lineTitle'))
                        product_features.append(get_feature_desc(line, "线路简称", 'lineSimpleTitle'))
                        product_features.append(get_feature_desc(line, "线路缩写", 'lineSortTitle'))
                        product_features.append(get_feature_desc(line, "去程交通", 'goTransportName'))
                        product_features.append(get_feature_desc(line,
                                                                 "去程航班（如果去程交通是飞机时，包括航空公司编码、航空公司名称、航班号、启程机场编码、去程机场名称、启程出发时间、到达机场编码、到达机场名称、到达时间、日期差、航班顺序）",
                                                                 'goAirports', ["airlineCode", "airlineName", "flightNo",
                                                                                "startAirportCode", "startAirportName",
                                                                                "startTime", "arriveAirportCode",
                                                                                "arriveAirportName", "arriveTime", "days",
                                                                                "flightSort"]))
                        product_features.append(get_feature_desc(line, "回程交通", 'backTransportName'))
                        product_features.append(get_feature_desc(line,
                                                                 "回程航班（如果回程交通是飞机时，包括航空公司编码、航空公司名称、航班号、回程机场编码、回程机场名称、回程出发时间、到达机场编码、到达机场名称、到达时间、日期差、航班顺序）",
                                                                 'backAirports', ["airlineCode", "airlineName", "flightNo",
                                                                                  "startAirportCode", "startAirportName",
                                                                                  "startTime", "arriveAirportCode",
                                                                                  "arriveAirportName", "arriveTime", "days",
                                                                                  "flightSort"]))
                        product_features.append(get_feature_desc(line, "行程旅游天数", 'tripDays'))
                        product_features.append(get_feature_desc(line, "行程旅游晚数", 'tripNight'))
                        product_features.append(get_feature_desc(line,
                                                                 "星级（多个逗号间隔）2-二星及以下；3-三星及同级；4-四星及同级；5-五星及同级；own-自理；-1-无；",
                                                                 'hotelStarName'))
                        product_features.append(get_feature_desc(line, "途径城市", 'passCities',
                                                                 ["continentName", "countryName", "provinceName",
                                                                  "cityName"]))
                        product_features.append(get_feature_desc(line, "是否需要签证  0=不需要，1=需要", 'needVisa'))
                        product_features.append(get_feature_desc(line, "线路特色", 'lineFeature'))
                        product_features.append(
                            get_feature_desc(line, "免签标志1:免签2:面签（如需要签证）", 'visaBasic.visas.freeVisa'))
                        product_features.append(get_feature_desc(line, "费用包含", 'costInclude'))
                        product_features.append(get_feature_desc(line, "费用不含", 'costExclude'))
                        product_features.append(get_feature_desc(line, "预定须知", 'bookRule'))
                        product_features.append(get_feature_desc(line, "补充说明", 'otherRule'))
                        product_features.append(get_feature_desc(line, "温馨提示", 'tipsContent'))
                        product_features.append(get_feature_desc(line, "服务标准", 'serviceStandard'))
                        product_features.append(get_feature_desc(line,
                                                                 "购物店（购物店地址、购物店名称、特色商品名称、购物店介绍或说明、购物店补充说明）",
                                                                 'shops', ["address", "shopName", "shopProduct", "remark",
                                                                           "shopContent"]))
                        product_features.append(
                            get_feature_desc(line, "自费项目（地址、项目名称和内容、自费项目介绍或说明）", 'selfCosts',
                                             ["address", "name", "remark"]))
                        product_features.append(get_feature_desc(line, "自费项目说明", 'selfCostContent'))

                        try:
                            for i, trip in enumerate(line["trips"]):
                                product_features.append(get_feature_desc(trip, "行程第几天", 'tripDay'))
                                product_features.append(get_feature_desc(trip, "行程内容描述", 'content'))
                                product_features.append(get_feature_desc(trip, "是否含早餐 0 不含 1 含", 'breakfast'))
                                product_features.append(get_feature_desc(trip, "是否含午餐 0 不含 1 含", 'lunch'))
                                product_features.append(get_feature_desc(trip, "是否含晚餐 0 不含 1 含", 'dinner'))
                                product_features.append(get_feature_desc(trip,
                                                                         "当天行程-交通信息（出发地、出发时间、目的地、到达时间、交通类型，bus-大巴；minibus-中巴；train-火车；ship-轮船；liner-游轮；airplane-飞机；99-其他；、）",
                                                                         'scheduleTraffics',
                                                                         ["departure", "departureTime", "destination",
                                                                          "arrivalTime", "trafficType"]))
                                product_features.append(
                                    get_feature_desc(trip, "酒店信息（酒店名称、星级 1 一星 2 两星 3 三星 4 四星 5 五星）",
                                                     'hotels', ["name", "star"]))
                                product_features.append(
                                    get_feature_desc(trip, "景点信息（景点名称、景点介绍或描述）", 'scenics',
                                                     ["name", "description"]))
                                product_features.append(get_feature_desc(trip, "行程主题", 'title'))

                        except Exception as e:
                            product_features.append("未找到行程信息")
                except Exception as e:
                    product_features.append("未找到线路信息")

                product_feature = '\n'.join(product_features)
    except Exception as e:
        print(f"product detail null: {e}")
        product_feature = ""
    return product_feature

async def product_search(args: List[dict]):
    results = []
    for arg in args:
        result = await search_one(arg)
        results.append(result)
    result = '<<<\n' + '\n------\n'.join(results) + '\n>>>'
    return result