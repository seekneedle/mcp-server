import uvicorn
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from server.router import router
from utils.config import config

app = FastAPI(
    title='outpainting_captioning_upscaler',
    description='outpainting images, captioning images,upscaler images',
    version='1.0.0',
    docs_url=None,
    redoc_url=None,  # 设置 ReDoc 文档的路径

)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount('/static', StaticFiles(directory="static"), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Custom Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css"
    )


# 包含路由
app.include_router(router)


def start_server():
    ip = config['ip']
    port = config['port']
    uvicorn.run(app, host=ip, port=port)
