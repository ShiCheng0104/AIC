# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from datetime import datetime
import inspect
import traceback
from typing import Dict, List
from tool.base import BaseTool, ToolFailure, ToolResult


class TimeConverter(BaseTool):
    """时间转换工具"""

    name: str = "time_converter"
    description: str = (
        "将秒转换为分钟、小时。输入：时间间隔（秒）。输出：分钟数、小时数"
    )
    input: str = "时间间隔（秒）"
    output: str = "分钟数、小时数"
    parameters: dict = {
        "type": "object",
        "properties": {
            "seconds": {
                "type": "number",
                "description": "时间间隔（秒），必须是非负数值。",
            }
        },
        "required": ["seconds"],
    }

    def execute(self, seconds: int) -> ToolResult:
        """
        将秒转换为三种格式的时间表示：
        1. by_seconds: 以秒显示
        2. by_minutes: 以分钟+秒显示
        3. by_hours: 以小时+分钟+秒显示

        :param seconds (int): 需要转换的时间（单位：秒）
        :return ToolResult: 包含三种格式的字典
        """
        is_negative = False

        if seconds < 0:
            is_negative = True
            seconds = -seconds
        minutes = seconds // 60
        demical_minutes = seconds / 60
        remaining_seconds = seconds % 60

        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        demical_hours = seconds / 3600

        return ToolResult(
            output={
                "by_seconds": f"{seconds}秒",
                "by_minutes": f"{minutes}分钟{remaining_seconds}秒",
                "by_integer_minutes": f"{round(demical_minutes)}分钟",
                "by_demical_minutes": f"{demical_minutes}分钟",
                "by_hours": f"{hours}小时{remaining_minutes}分钟{remaining_seconds}秒",
                "by_demical_hours": f"{demical_hours}小时",
                "is_negative": is_negative,
            },
        )
