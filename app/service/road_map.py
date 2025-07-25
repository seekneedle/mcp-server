import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from utils.log import log
from utils.config import config
import traceback
import httpx
from http import HTTPStatus
from dashscope.aigc.generation import AioGeneration
from utils.security import decrypt

FOREIGN_TEMPLATE = "res/html/amap.html"
DOMESTIC_TEMPLATE = "res/html/tmap.html"
OUTPUT_DIR = Path("/usr/share/nginx/html/static")
BASE_URL = "http://8.152.213.191/static"
WEATHER_KEY = decrypt(config["weather_key"])

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 颜色列表用于标记点
COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#9b59b6",
    "#e67e22", "#1abc9c", "#34495e", "#f1c40f",
    "#d35400", "#7f8c8d", "#27ae60", "#8e44ad"
]

# Configuration (should be moved to config file in production)
AMAP_KEY = decrypt(config["amap_key"])
TMAP_KEY = decrypt(config["tmap_key"])

async def create_amap(locations: List[Dict[str, str]]) -> str:
    """创建国外地图(使用高德地图)"""
    try:
        # 准备城市数据
        cities = []
        for i, loc in enumerate(locations):
            cities.append({
                "name": loc.get("name", f"地点{i + 1}"),
                "position": [str(loc["lng"]), str(loc["lat"])],
                "color": COLORS[i % len(COLORS)],
                "desc": loc.get("desc", "")
            })

        # 读取模板
        with open(FOREIGN_TEMPLATE, "r", encoding="utf-8") as f:
            template = f.read()

        # 替换模板中的变量
        html_content = template.replace("${cities_json}", json.dumps(cities, ensure_ascii=False))

        # 生成唯一文件名
        filename = f"map_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}.html"
        output_path = OUTPUT_DIR / filename

        # 保存HTML文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        log.info(f"生成国外旅行地图: {BASE_URL}/{filename}")
        return f"{BASE_URL}/{filename}"

    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"create_amap失败: {str(e)}, trace: {trace_info}")
        return ""


async def create_tmap(locations: List[Dict[str, str]], lines: List[Dict[str, str]]) -> str:
    """创建国内地图(使用天地图)

    参数:
        locations: 标记点列表，每个元素包含lng(经度)、lat(纬度)和name(名称)
        lines: 线路列表，每个元素包含start_lng(起点经度)、start_lat(起点纬度)、
              end_lng(终点经度)、end_lat(终点纬度)

    返回:
        生成的地图HTML文件URL
    """
    try:
        # 准备标记点数据
        points = []
        for i, loc in enumerate(locations):
            points.append({
                "lng": str(loc["lng"]),
                "lat": str(loc["lat"]),
                "index": loc.get('name', f'地点{i + 1}')
            })

        # 准备线路数据
        line_segments = []
        for line in lines:
            line_segments.append({
                "start_lng": str(line["start_lng"]),
                "start_lat": str(line["start_lat"]),
                "end_lng": str(line["end_lng"]),
                "end_lat": str(line["end_lat"])
            })

        # 读取模板
        with open(DOMESTIC_TEMPLATE, "r", encoding="utf-8") as f:
            template = f.read()

        # 替换模板中的变量
        html_content = template.replace("${points_json}", json.dumps(points, ensure_ascii=False))
        html_content = html_content.replace("${lines_json}", json.dumps(line_segments, ensure_ascii=False))

        # 确保输出目录存在
        OUTPUT_DIR.mkdir(exist_ok=True)

        # 生成唯一文件名
        filename = f"map_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}.html"
        output_path = OUTPUT_DIR / filename

        # 保存HTML文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        log.info(f"生成旅行地图: {BASE_URL}/{filename}")
        return f"{BASE_URL}/{filename}"

    except Exception as e:
        log.error(f"创建地图失败: {str(e)}")
        return ""


async def geocode_openai(locations: List[str]) -> List[Dict[str, str]]:
    """使用百炼平台千问模型进行地理编码（使用平台原生JSON解析）"""
    system_prompt = """你是一个专业的地理编码服务，非常了解国外地理位置对应的坐标。请严格按以下规则处理：
1. 只返回JSON格式：{"longitude": "经度", "latitude": "纬度"}
2. 未知地址返回：{"longitude": "", "latitude": ""}
3. 所有地名都是国外的，不要返回国内坐标。

请返回 {location} 的地理编码"""

    results = []
    api_key = decrypt(config['api_key'])

    for location in locations:
        try:
            # 调用百炼平台API（启用内置JSON模式）
            response = await AioGeneration.call(
                model='qwen-max',
                prompt=system_prompt.replace("{location}", location),
                result_format='message',
                response_format={'type': 'json_object'},
                temperature=0,
                api_key=api_key
            )

            if response.status_code == HTTPStatus.OK:
                # 直接获取平台解析好的JSON
                json_str = response.output.choices[0].message.content
                log.info(f"{location}解析结果：{json_str}")
                result_json = json.loads(json_str)
                # 百炼的JSON模式会自动转换为Python字典
                lon = result_json.get('longitude', '')
                lat = result_json.get('latitude', '')

                results.append({
                    "name": location,
                    "lng": lon,
                    "lat": lat
                })
            else:
                raise ValueError(f"{response.code}: {response.message}")

        except Exception as e:
            log.error(f"地址解析失败【{location}】: {str(e)}", exc_info=True)
            results.append({
                "name": location,
                "lng": "",
                "lat": "",
                "desc": "Geocoding failed"
            })

    log.info(f"地理编码完成，成功率：{len([r for r in results if r['lng']])}/{len(results)}")
    return results


# New geocoding functions
async def geocode_amap(locations: List[str]) -> List[Dict[str, str]]:
    """Get coordinates for international locations using AMap"""
    results = []
    async with httpx.AsyncClient(timeout=config['timeout']) as client:
        for location in locations:
            try:
                url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_KEY}&address={location}"
                response = await client.get(url)
                data = response.json()
                if data["status"] == "1" and data["geocodes"]:
                    geo = data["geocodes"][0]
                    results.append({
                        "name": location,
                        "lng": geo["location"].split(",")[0],
                        "lat": geo["location"].split(",")[1]
                    })
            except Exception as e:
                log.error(f"AMap geocoding failed for {location}: {str(e)}")
                results.append({"name": location, "lng": "", "lat": "", "desc": "Geocoding failed"})
    log.info(f"生成地址地理编码: {results}")
    return results


async def geocode_tmap(locations: List[str]) -> List[Dict[str, str]]:
    """Get coordinates for domestic locations using TMap"""
    results = []
    async with httpx.AsyncClient(timeout=config['timeout']) as client:
        for location in locations:
            try:
                url = f"https://api.tianditu.gov.cn/geocoder?ds={'{'}'key':'{TMAP_KEY}'{'}'}&addr={location}"
                response = await client.get(url)
                data = response.json()
                if data["status"] == "0":
                    results.append({
                        "name": location,
                        "lng": data["location"]["lon"],
                        "lat": data["location"]["lat"]
                    })
            except Exception as e:
                log.error(f"TMap geocoding failed for {location}: {str(e)}")
                results.append({"name": location, "lng": "", "lat": "", "desc": "Geocoding failed"})
    log.info(f"生成地址地理编码: {results}")
    return results


async def geocode_weather(locations: List[str]) -> List[Dict[str, str]]:
    """Get coordinates for locations using OpenWeatherMap Geo API"""
    results = []
    async with httpx.AsyncClient(timeout=config['timeout']) as client:
        for location in locations:
            try:
                url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={WEATHER_KEY}"
                response = await client.get(url)
                data = response.json()

                if data and isinstance(data, list) and len(data) > 0:
                    first_result = data[0]
                    # Extract preferred name (zh -> en -> default)
                    local_names = first_result.get("local_names", {})
                    display_name = (
                            local_names.get("zh")
                            or local_names.get("en")
                            or first_result.get("name", location)
                    )

                    results.append({
                        "name": display_name,
                        "lng": str(first_result.get("lon", "")),
                        "lat": str(first_result.get("lat", ""))
                    })
                else:
                    results.append({
                        "name": location,
                        "lng": "",
                        "lat": ""
                    })

            except Exception as e:
                trace_info = traceback.format_exc()
                log.error(f"OpenWeatherMap geocoding failed for {location}: {str(e)}, {trace_info}")
                results.append({
                    "name": location,
                    "lng": "",
                    "lat": ""
                })

    log.info(f"Generated geocoding results: {results}")
    return results


async def get_weather_by_coordinate(lat: str, lon: str, date: str, tz: str = "+08:00",
                                     units: str = "metric") -> Dict:
    """
    获取坐标点指定日期的天气信息

    参数:
        lat: 纬度
        lon: 经度
        date: 日期字符串 (YYYY-MM-DD)
        tz: 时区偏移 (默认"+00:00")
        units: 单位制 (默认"metric")

    返回:
        天气数据字典
    """
    try:
        # Validate date format
        datetime.strptime(date, "%Y-%m-%d")

        # Validate timezone format
        if not (tz.startswith(("+", "-")) and len(tz) == 6 and tz[3] == ":"):
            raise ValueError("Invalid timezone format. Expected ±HH:MM")

        # Validate units
        if units not in ("metric", "imperial"):
            raise ValueError("Invalid units. Expected 'metric' or 'imperial'")

        weather_key = decrypt(config["weather_key"])
        url = f"https://api.openweathermap.org/data/3.0/onecall/day_summary?lat={lat}&lon={lon}&date={date}&tz={tz}&units={units}&appid={weather_key}"

        async with httpx.AsyncClient(timeout=config['timeout']) as client:
            response = await client.get(url)
            response.raise_for_status()
            weather_data = response.json()

        log.info(f"Weather data retrieved for {lat},{lon} on {date}")
        return weather_data

    except httpx.HTTPStatusError as e:
        error_msg = f"Weather API error: {e.response.status_code} - {e.response.text}"
        log.error(error_msg)
        raise Exception(error_msg)
    except ValueError as e:
        error_msg = f"Invalid input: {str(e)}"
        log.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        trace_info = traceback.format_exc()
        error_msg = f"Weather query failed: {str(e)}"
        log.error(f"{error_msg}, trace: {trace_info}")
        raise Exception(error_msg)


async def get_weather(coordinates: List[Dict[str, str]]) -> List[Dict]:
    """
    获取多个坐标点的天气信息

    参数:
        coordinates: 坐标点信息列表，每个坐标点包含:
            - lat: 纬度
            - lon: 经度
            - date: 日期(格式可以是YYYY-MM-DD、MM-DD或DD)

    返回:
        天气信息列表，每个元素对应一个坐标点的天气数据
    """
    results = []
    current_date = datetime.now()

    for coord in coordinates:
        try:
            lat = coord["lat"]
            lon = coord["lon"]
            date_str = coord["date"]
            tz = "+08:00"  # 默认时区
            units = "metric"  # 默认单位制

            # 自动补全年月
            date_parts = date_str.split("-")
            if len(date_parts) == 1:  # 只有日 (如 "15")
                formatted_date = f"{current_date.year}-{current_date.month:02d}-{int(date_parts[0]):02d}"
            elif len(date_parts) == 2:  # 有月日 (如 "07-15")
                formatted_date = f"{current_date.year}-{int(date_parts[0]):02d}-{int(date_parts[1]):02d}"
            else:  # 完整日期 (如 "2025-07-15")
                formatted_date = date_str

            # 获取天气数据
            weather_data = await get_weather_by_coordinate(lat, lon, formatted_date, tz, units)

            results.append(weather_data)

        except Exception as e:
            trace_info = traceback.format_exc()
            error_msg = f"Weather query failed for {coord}: {str(e)}"
            log.error(f"{error_msg}, trace: {trace_info}")
            results.append({
                "lat": coord.get("lat", ""),
                "lon": coord.get("lon", ""),
                "date": coord.get("date", ""),
                "error": error_msg
            })

    return results

