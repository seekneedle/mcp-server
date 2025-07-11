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
                "position": [float(loc["lng"]), float(loc["lat"])],
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


async def create_tmap(locations: List[Dict[str, str]]) -> str:
    """创建国内地图(使用天地图)"""
    try:
        # 准备城市数据
        points = []
        for i, loc in enumerate(locations):
            points.append({
                "lng": float(loc["lng"]),
                "lat": float(loc["lat"]),
                "index": f"第{i + 1}天{loc.get('name', f'地点{i + 1}')}"
                })

            # 读取模板
            with open(DOMESTIC_TEMPLATE, "r", encoding="utf-8") as f:
                template = f.read()

            # 替换模板中的变量
            html_content = template.replace("${points_json}", json.dumps(points, ensure_ascii=False))

            # 生成唯一文件名
            filename = f"map_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}.html"
            output_path = OUTPUT_DIR / filename

            # 保存HTML文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        log.info(f"生成国内旅行地图: {BASE_URL}/{filename}")
        return f"{BASE_URL}/{filename}"

    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"create_tmap失败: {str(e)}, trace: {trace_info}")
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
                    "lat": lat,
                    "desc": f"Geocoded: {location}" if lon else "Not found"
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
    async with httpx.AsyncClient() as client:
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
                        "lat": geo["location"].split(",")[1],
                        "desc": f"Geocoded location: {location}"
                    })
            except Exception as e:
                log.error(f"AMap geocoding failed for {location}: {str(e)}")
                results.append({"name": location, "lng": "", "lat": "", "desc": "Geocoding failed"})
    log.info(f"生成地址地理编码: {results}")
    return results


async def geocode_tmap(locations: List[str]) -> List[Dict[str, str]]:
    """Get coordinates for domestic locations using TMap"""
    results = []
    async with httpx.AsyncClient() as client:
        for location in locations:
            try:
                url = f"https://api.tianditu.gov.cn/geocoder?ds={'{'}'key':'{TMAP_KEY}'{'}'}&addr={location}"
                response = await client.get(url)
                data = response.json()
                if data["status"] == "0":
                    results.append({
                        "name": location,
                        "lng": data["location"]["lon"],
                        "lat": data["location"]["lat"],
                        "desc": f"Geocoded location: {location}"
                    })
            except Exception as e:
                log.error(f"TMap geocoding failed for {location}: {str(e)}")
                results.append({"name": location, "lng": "", "lat": "", "desc": "Geocoding failed"})
    log.info(f"生成地址地理编码: {results}")
    return results

