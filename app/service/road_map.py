import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from utils.log import log
import traceback

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