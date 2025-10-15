# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

"""日志模块"""

import sys
import datetime
import os
import time
from flask_socketio import SocketIO

# 全局socketio引用
socketio = None

def init_logger_with_flask(socketio_main):
    global socketio
    socketio = socketio_main

LEVELS = ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS", "SPECIAL"]

console_level = "DEBUG"
file_level = "TRACE"

logs_path = "devlop_output/logs"
log_file_path = None

COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    "grey": "\033[90m",
    "reset": "\033[0m",
}


def init(log_filename=None, console_log_level="DEBUG", file_log_level="TRACE"):
    """初始化日志模块"""
    global log_file_path, console_level, file_level

    os.makedirs(logs_path, exist_ok=True)

    if log_filename:
        log_file_path = os.path.join(logs_path, log_filename)
    else:
        date_str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
        log_file_path = os.path.join(logs_path, "log_" + date_str + ".log")

    if console_log_level in LEVELS:
        console_level = console_log_level

    if file_log_level in LEVELS:
        file_level = file_log_level


def should_log(level, target_level):
    """判断是否应该打印当前日志"""
    return LEVELS.index(level) >= LEVELS.index(target_level)


def color_print(level, color, *args, sep=" ", end="\n"):
    """通用日志打印函数，支持控制台和文件输出"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_message = f"{timestamp} [{level}] {sep.join(map(str, args))}"

    # 发送日志到前端
    if level in {"INFO", "SPECIAL"}:
        socketio.emit('log_message', {
            'level': level,
            'message': log_message,
            'color': color
        })

    if should_log(level, console_level):
        print(
            f"{COLORS[color]}{log_message}{COLORS['reset']}", end=end, file=sys.stdout
        )

    if log_file_path and should_log(level, file_level):
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_message + "\n")


# 各级别日志函数
def trace(*args, sep=" ", end="\n"):
    """打印跟踪信息（白色）"""
    color_print("TRACE", "white", *args, sep=sep, end=end)


def debug(*args, sep=" ", end="\n"):
    """打印调试信息（灰色）"""
    color_print("DEBUG", "grey", *args, sep=sep, end=end)


def info(*args, sep=" ", end="\n"):
    """打印普通信息（蓝色）"""
    color_print("INFO", "blue", *args, sep=sep, end=end)


def warning(*args, sep=" ", end="\n"):
    """打印警告信息（黄色）"""
    color_print("WARNING", "yellow", *args, sep=sep, end=end)


def error(*args, sep=" ", end="\n"):
    """打印错误信息（红色）"""
    color_print("ERROR", "red", *args, sep=sep, end=end)


def success(*args, sep=" ", end="\n"):
    """打印成功信息（绿色）"""
    color_print("SUCCESS", "green", *args, sep=sep, end=end)


def special(*args, sep=" ", end="\n"):
    """打印特殊信息（青色）"""
    color_print("SPECIAL", "cyan", *args, sep=sep, end=end)
