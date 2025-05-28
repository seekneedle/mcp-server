from mcp.server.fastmcp import FastMCP
from utils.config import config
from service.product_search import search

mcp = FastMCP("Math", host=config["ip"], port=config["port"])

@mcp.tool()
def product_search(query: str) -> str:
    """Search travel products"""
    return search(query)


def start_server():
    mcp.run(transport="sse")