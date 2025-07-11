import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from utils.log import log
from utils.security import decrypt
from utils.config import config
import traceback
import httpx
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import JsonOutputParser

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

# 解密API密钥
OPENAI_API_KEY = decrypt(config["api_key"])

# 初始化ChatOpenAI实例
chat_model = ChatOpenAI(model_name="qwen-max", openai_api_key=OPENAI_API_KEY)


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
    """Get coordinates for international locations using Qwen-Plus"""
    results = []
    system_instruction = "你是一个乐于助人的助手，能够将地址地理编码为经度和纬度。"
    json_parser = JsonOutputParser()

    async with httpx.AsyncClient() as client:
        for location in locations:
            try:
                # 准备消息
                messages = [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=f"请对以下地址进行地理编码: {location}")
                ]

                # 调用Qwen-Plus模型
                response = chat_model(messages)

                # 使用langchain的JsonOutputParser解析响应
                parsed_response = json_parser.parse(response.content)

                if "longitude" in parsed_response and "latitude" in parsed_response:
                    results.append({
                        "name": location,
                        "lng": parsed_response["longitude"],
                        "lat": parsed_response["latitude"],
                        "desc": f"Geocoded location: {location}"
                    })
                else:
                    raise ValueError("Unexpected response format.")
            except Exception as e:
                log.error(f"Geocoding failed for {location}: {str(e)}")
                results.append({"name": location, "lng": "", "lat": "", "desc": "Geocoding failed"})
    log.info(f"生成地址地理编码: {results}")
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

