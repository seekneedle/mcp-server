import requests


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

def search(query: str):
    results = []
    url = "http://8.152.213.191:8471/vector_store/retrieve"
    id = "icmp3tfyk6"
    auth = "jQAjpkdalP^UKt21"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': auth
    }
    data = {
        "id": id,
        "query": query,
        "min_score": 0
    }

    rerank_top_k = 3
    data["rerank_top_k"] = rerank_top_k
    data["top_k"] = rerank_top_k * 20
    data["sparse_top_k"] = rerank_top_k * 10
    response = requests.post(url, headers=headers, json=data)

    for chunk in response.json()['data']['chunks']:
        metadata = chunk['metadata']
        product_num = metadata['doc_name']
        url = f"https://mapi.uuxlink.com/mcsp/productAi/productInfo?productNum={product_num}"
        try:
            product_detail = requests.get(url).json()['data']
            product_features = [f"productNum：{product_num}"]
            product_features.append(get_feature_desc(product_detail, "参团游类型", 'productGroupTypeName'))
            product_features.append(get_feature_desc(product_detail, "产品类别", 'productTypeName'))
            product_features.append(get_feature_desc(product_detail, "产品名称", 'productTitle'))
            product_features.append(get_feature_desc(product_detail, "副标题", 'productSubtitle'))
            product_features.append(get_feature_desc(product_detail, "产品主题", 'themes.name'))
            product_features.append(get_feature_desc(product_detail, "目的地", 'dests',
                                                     ["continentName", "countryName", "destProvinceName",
                                                      "destCityName"]))
            product_features.append(get_feature_desc(product_detail, "产品标签", 'tags.name'))
            product_features.append(get_feature_desc(product_detail, "业务区域", 'businessAreas'))
            product_features.append(get_feature_desc(product_detail, "出发地国家", 'departureCountryName'))
            product_features.append(get_feature_desc(product_detail, "出发地省份", 'departureProvinceName'))
            product_features.append(get_feature_desc(product_detail, "出发地城市", 'departureCityName'))
            product_features.append(get_feature_desc(product_detail, "儿童年龄标准区间开始值", 'childAgeBegin'))
            product_features.append(get_feature_desc(product_detail, "儿童年龄标准区间结束值", 'childAgeEnd'))
            product_features.append(get_feature_desc(product_detail, "儿童身高标准区间开始值", 'childHeightBegin'))
            product_features.append(get_feature_desc(product_detail, "儿童身高标准区间结束值", 'childHeightEnd'))
            product_features.append(get_feature_desc(product_detail, "儿童价格是否含大交通", 'childHasTraffic'))
            product_features.append(get_feature_desc(product_detail, "儿童价是否含床", 'childHasBed'))
            product_features.append(get_feature_desc(product_detail, "儿童标准说明", 'childRule'))
            product_features.append(get_feature_desc(product_detail, "是否包含保险", 'insuranceIncluded'))
            product_features.append(get_feature_desc(product_detail, "营销标签", 'markets.name'))
            product_features.append(
                get_feature_desc(product_detail, "保险名称、保险类型（境内外旅游险、航空险等）、保险内容", 'insurance',
                                 ["name", "typeName", "content"]))
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

        results.append(product_feature)
    result = '\n'.join(product_features)
    return result
