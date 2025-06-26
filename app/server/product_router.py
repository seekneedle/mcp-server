from fastmcp import FastMCP
from typing import List, Dict
from utils.geo import get_city_code, get_province_code, get_country_code
from service.product_search import product_search
from service.product_detail import get_product_info

product_mcp = FastMCP(
    name='product-mcp-server',
    instructions="""
        This server provides travel product related information.
    """,
    on_duplicate_tools='ignore'
)


@product_mcp.prompt(name="提取国家、省份、城市列表")
def extract_location(desc: str) -> str:
    """从文本中提取所有明确提到的地点信息，按层级结构解析为国家、省份、城市，输出JSON格式列表"""
    return f"""
请严格按以下要求处理文本：
1. 提取描述中所有明确提到的**国家、省份、城市**名称
2. 每个地点独立生成一个JSON对象，包含三个字段：
   - country：国家名称（如未提及则留空字符串）
   - province：省份/直辖市/自治区名称
   - city：城市名称
3. 处理规则：
   - 直辖市（如北京/上海）的province字段填直辖市名，city字段留空
   - 层级关系处理（示例）：
        "中国广东省广州市" → {{"country":"中国", "province":"广东省", "city":"广州市"}}
        "上海市浦东新区" → {{"country":"", "province":"上海市", "city":"浦东新区"}}
        "巴黎" → {{"country":"", "province":"", "city":"巴黎"}}
   - 同一句子中的连续层级自动组合（如"中国浙江杭州"）
   - 非连续出现的地名分开生成对象
4. 输出格式：JSON列表，按原文出现顺序排序

待处理描述：
{desc}

请直接输出JSON列表，不要包含任何解释性文字。
"""


async def _search_product_nums(location_dict: Dict[str, str], search_type: str) -> List[str]:
    """
    根据地理信息查询产品编号的公共方法

    Args:
        location_dict: 包含地理信息的字典
        search_type: 查询类型，'dest'或'pass'

    Returns:
        匹配的产品编号列表
    """
    # 参数校验
    if not location_dict or not any(location_dict.values()):
        return []

    # 获取各级地理编码（空值自动处理）
    country = location_dict.get("country", "")
    province = location_dict.get("province", "")
    city = location_dict.get("city", "")

    # 根据查询类型构建参数前缀
    prefix = "dest" if search_type == "dest" else "pass"

    # 构建查询参数
    search_args = [{
        f"{prefix}CountryCode": get_country_code(country) if country else "",
        f"{prefix}ProvinceCode": get_province_code(province) if province else "",
        f"{prefix}CityCode": get_city_code(city) if city else ""
    }]

    try:
        # 调用产品搜索服务
        results = await product_search(search_args)
        # 提取产品编号
        return [item["productNum"] for item in results if item.get("productNum")]
    except Exception as e:
        print(f"产品查询失败: {str(e)}")
        return []


@product_mcp.tool(name="使用目的地查询旅行产品的产品编号")
async def search_dest_product_nums(location_dict: Dict[str, str]) -> List[str]:
    """
    根据目的地查询产品编号

    Args:
        location_dict: 包含地理信息的字典

    Returns:
        匹配的产品编号列表
    """
    return await _search_product_nums(location_dict, "dest")


@product_mcp.tool(name="使用途经地查询旅行产品的产品编号")
async def search_pass_product_nums(location_dict: Dict[str, str]) -> List[str]:
    """
    根据途经地查询产品编号

    Args:
        location_dict: 包含地理信息的字典

    Returns:
        匹配的产品编号列表
    """
    return await _search_product_nums(location_dict, "pass")


@product_mcp.tool(name="获取产品的景点信息")
async def get_product_scenics(product_num: str) -> List[Dict[str, str]]:
    """
    根据产品编号检索景点信息，返回结构化景点列表

    Args:
        product_num: 产品编号 (如 "TP-1001")

    Returns:
        景点信息列表，每个景点包含:
            - name: 景点名称
            - description: 景点描述
        示例: [{"name": "埃菲尔铁塔", "description": "巴黎标志性建筑..."}, ...]
        没有景点时返回空列表
    """
    # 获取产品详细信息
    product_info = await get_product_info(product_num)
    if not product_info:
        return []

    scenics_list = []

    # 提取所有景点
    try:
        # 遍历所有线路
        for line in product_info.get("lineList", []):
            # 遍历线路中的每一天行程
            for trip in line.get("trips", []):
                # 遍历每天的景点
                for scenic in trip.get("scenics", []):
                    # 提取景点信息
                    scenic_info = {
                        "name": scenic.get("name", ""),
                        "description": scenic.get("description", "")
                    }
                    # 仅添加有名称的景点
                    if scenic_info["name"]:
                        scenics_list.append(scenic_info)

    except Exception as e:
        print(f"景点提取失败: {str(e)}")

    return scenics_list