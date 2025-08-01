from utils.config import config
import contextlib
from starlette.applications import Starlette
from starlette.routing import Mount
from server.product_router import product_mcp, product_mcp_2
from server.image_router import image_mcp
from server.video_router import video_mcp
from server.map_router import map_mcp
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

# 手动维护的MCP列表（显式导入后添加）
ALL_MCPS = [
    {
        'path': '/v1/product',
        'middlewares': [],
        'app': product_mcp.sse_app()
    },
    {
        'path': '/v2/product',
        'middlewares': [],
        'app': product_mcp_2.sse_app()
    },
    {
        'path': '/v1/image',
        'middlewares': [],
        'app': image_mcp.sse_app()
    },
    {
        'path': '/v1/video',
        'middlewares': [],
        'app': video_mcp.sse_app()
    },
    {
        'path': '/v1/map',
        'middlewares': [],
        'app': map_mcp.sse_app()
    }
]

def start_server():
    """
        自动挂载ALL_MCPS中所有MCP服务
        """
    # 自动生成路由
    routes = [
        Mount(
            item['path'],
            app=item['app'],
            middleware=item.get('middlewares', [])
        )
        for item in ALL_MCPS
    ]

    # 合并生命周期（假设至少有一个MCP）
    lifespans = [m['app'].lifespan for m in ALL_MCPS]
    combined_lifespan = lifespans[0] if len(lifespans) == 1 else combine_lifespans(*lifespans)

    # 创建应用
    app = Starlette(
        routes=routes,
        debug=config.get('debug', False),
        lifespan=combined_lifespan
    )

    # 启动服务
    uvicorn.run(
        app,
        host=config['ip'],
        port=config['port']
    )