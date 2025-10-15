#!/bin/bash

echo "开始解压数据"
mkdir -p /app/devlop_home/复赛数据
tar -xzf /app/devlop_home/复赛数据.tar.gz -C /app/devlop_home/
echo "数据解压完成"

cd /app/
echo "开始执行数据处理"
python3 /app/devlop_home/data_process.py

echo "数据处理完成"

echo "开始执行main.py"
python3 /app/devlop_home/main.py $1 $2
echo "main.py执行完成，输出结果如下："
cat $2