# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

"""日志模块

前端日志精简规则：
- 工具函数执行结果：仅保留核心值（如 duration_calculator 的 by_seconds），示例：
    【工具函数duration_calculator执行结果】1149.0秒
- 原子问题答案：若包含“调用…参数…。”等说明，仅保留最后一句回答内容。
- 其他：保留首段文本，尽量避免输出原始 dict 结构到前端。
"""

import sys
import json
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

    # 发送精简日志到前端（不带时间戳和级别标签）
    if level in {"INFO", "SPECIAL"} and socketio is not None:
        simplified = _simplify_for_frontend(level, args)
        socketio.emit('log_message', {
            'level': level,
            'message': simplified,
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


# =========================
# 前端精简格式化逻辑
# =========================

def _extract_value_from_tool_result(function_result):
    """从工具返回结果中提取一个最有用的值。

    兼容形态：
    - dict 或可被 json 解析的字符串
    - 结构优先级：output -> result -> 常见聚合键（*_sum/*_avg/*_min/*_max/*_count）
    - 对 duration_calculator 这类多单位结果优先取 by_seconds
    """
    data = function_result
    # 字符串尝试解析为 JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return data

    if not isinstance(data, dict):
        return str(data)

    d = data
    if 'output' in d and isinstance(d['output'], dict):
        d = d['output']

    # 优先 result
    if 'result' in d:
        r = d['result']
        if isinstance(r, dict):
            # 多单位优先 by_seconds
            for key in ['by_seconds', 'seconds']:
                if key in r:
                    return str(r[key])
            # 其次选第一个标量值
            for v in r.values():
                if isinstance(v, (str, int, float)):
                    return str(v)
            # 兜底：转字符串
            return str(r)
        else:
            return str(r)

    # 常见聚合键
    for suffix in ['_sum', '_avg', '_min', '_max', '_count']:
        for k, v in d.items():
            if isinstance(k, str) and k.endswith(suffix):
                return str(v)

    # 单键字典的值
    if len(d) == 1:
        return str(next(iter(d.values())))

    # 兜底
    return str(d)


def _simplify_for_frontend(level: str, args: tuple) -> str:
    """根据约定规则将日志内容简化为前端友好的短句。"""
    if not args:
        return ''

    try:
        head = args[0] if isinstance(args[0], str) else str(args[0])

        # 工具函数执行结果：提取核心值
        if isinstance(head, str) and ('【工具函数' in head and '执行结果】' in head):
            val = _extract_value_from_tool_result(args[1]) if len(args) > 1 else ''
            return f"{head}{val}"

        # 原子问题答案：若包含“调用…参数…。”，仅保留最后一句
        if isinstance(head, str) and ('【原子问题答案】' in head) and len(args) > 1:
            text = str(args[1])
            if ('调用' in text and '参数' in text and '。' in text):
                simple = text.split('。')[-1].strip()
            else:
                simple = text
            return f"{head}{simple}"

        # 其他：尽量避免输出 dict 原文；支持“【标签】+ 列表”成对显示
        def join_list(lst):
            try:
                items = []
                for v in lst:
                    if isinstance(v, (int, float)):
                        items.append(str(v))
                    elif isinstance(v, str):
                        items.append(v)
                    else:
                        # 对象/字典，尽量简化为可视条目
                        items.append(str(v))
                return '，'.join(items)
            except Exception:
                return str(lst)

        parts = []
        i = 0
        arg_list = list(args)
        while i < len(arg_list):
            a = arg_list[i]
            b = arg_list[i + 1] if i + 1 < len(arg_list) else None
            # 处理形如："【标签】", [list]
            if isinstance(a, str) and isinstance(b, list):
                parts.append(f"{a}{join_list(b)}")
                i += 2
                continue
            # 普通标量
            if isinstance(a, (int, float, str)):
                parts.append(str(a))
            # 跳过复杂结构（如 dict）避免输出 {}
            i += 1

        return ' '.join(parts)
    except Exception:
        # 兜底：按原始拼接
        return ' '.join(map(str, args))
