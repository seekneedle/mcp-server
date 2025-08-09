#!/bin/bash

# 进入 app 目录
cd app || { echo "无法进入 app 目录"; exit 1; }

# 检查 main.py 是否存在
if [ ! -f "app.py" ]; then
    echo "错误：app.py 不存在"
    exit 1
fi

# 创建 output 目录（如果不存在）
mkdir -p output

# 后台运行 main.py，并输出日志到 output/run.log
ENV=prod nohup python app.py >output/run.log 2>&1 &

# 显示进程信息
echo "生产环境 app.py 已在后台运行，日志输出到 output/run.log"
echo "进程 ID: $!"