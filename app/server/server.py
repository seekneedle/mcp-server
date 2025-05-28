import uvicorn
from mcp.server.fastmcp import FastMCP
from utils.config import config

mcp = FastMCP("Math", host=config["ip"], port=config["port"])

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

def start_server():
    mcp.run(transport="sse")