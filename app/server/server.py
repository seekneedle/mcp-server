from fastmcp import FastMCP
from utils.config import config
from typing import List
from service.product_search_rag import search_rag
from service.product_search_product_num import search_product_nums
import contextlib
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn

def combine_lifespans(*lifespans):
    """
    Combine multiple lifespan context managers into one.
    This allows for managing multiple session managers in a single lifespan context.
    Args:
        *lifespans: A variable number of lifespan context managers to combine.
    Returns:
        A combined lifespan context manager that yields control to the application.
    """
    @contextlib.asynccontextmanager
    async def combined_lifespan(app):
        async with contextlib.AsyncExitStack() as stack:
            for lifespan in lifespans:
                await stack.enter_async_context(lifespan(app))
            yield

    return combined_lifespan

rag_mcp = FastMCP(
    name='rag-mcp-server',
    instructions="""
        This server provides travel products using rag search information.
    """,
    on_duplicate_tools='ignore'
)

product_num_mcp = FastMCP(
    name='product-num-mcp-server',
    instructions="""
        This server provides travel products using product num search information.
    """,
    on_duplicate_tools='ignore'
)

@rag_mcp.tool()
async def rag_search(query: str, top_k: int=3) -> str:
    """Search travel products use RAG"""
    return await search_rag(query, top_k)

@product_num_mcp.tool()
async def product_nums_search(product_num: List[str]) -> str:
    """Search travel products use product nums"""
    return await search_product_nums(product_num)

def start_server():
    rag_app = rag_mcp.sse_app()
    product_num_app = product_num_mcp.sse_app()

    starlettle_app = Starlette(
        routes=[
            Mount('/v1/rag', app=rag_app),
            Mount('/v1/product-num', app=product_num_app),
        ],
        debug=True,
        lifespan=combine_lifespans(rag_app.lifespan, product_num_app.lifespan)
    )
    
    uvicorn.run(
        starlettle_app,
        host=config["ip"],
        port=config["port"]
    )