# 使用官方的Python基础镜像
FROM python:3.10-slim as builder

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制应用代码
COPY app/ /app/

# # 启动命令
CMD ["python", "app.py"]