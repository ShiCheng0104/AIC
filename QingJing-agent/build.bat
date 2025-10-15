@echo off
chcp 65001 >nul

IF "%ZHIPUAI_API_KEY%"=="" (
    echo 错误：未找到 ZHIPUAI_API_KEY 环境变量
    pause
    exit /b 1
)

IF "%1"=="" (
    echo 错误：未指定镜像版本号
    pause
    exit /b 1
)

set VERSION=%1

echo 生成数据处理脚本
jupyter nbconvert --to script devlop_home/data_process.ipynb

echo 压缩复赛数据
tar -czf devlop_home/复赛数据.tar.gz -C devlop_data/assets 复赛b榜数据

echo 构建 Docker 镜像
docker build --build-arg ZHIPUAI_API_KEY=%ZHIPUAI_API_KEY% -t hubdocker.aminer.cn/013861b58d084a79866ded8df8801da1/qingjing:%VERSION% .
del devlop_home\复赛数据.tar.gz

echo Docker 镜像构建完成

set /p PUSH="是否推送镜像? (y/n): "
if /i "%PUSH%"=="y" (
    docker push hubdocker.aminer.cn/013861b58d084a79866ded8df8801da1/qingjing:%VERSION%
    echo 镜像已推送
)
