from mcp.server.fastmcp import FastMCP
from utils.config import config
from typing import List
from service.product_search_rag import search_rag
from service.product_search_product_num import search_product_nums

mcp = FastMCP("Travel", host=config["ip"], port=config["port"])

@mcp.tool()
async def rag_search(query: str, top_k: int=3) -> str:
    """Search travel products use RAG"""
    return await search_rag(query, top_k)

@mcp.tool()
async def product_nums_search(product_num: List[str]) -> str:
    """Search travel products use product nums"""
    return await search_product_nums(product_num)

def start_server():
    mcp.run(transport="sse")