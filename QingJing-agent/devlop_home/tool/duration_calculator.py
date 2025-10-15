# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from datetime import datetime
from typing import List

from tool.base import BaseTool, ToolFailure, ToolResult
from tool.time_converter import TimeConverter


class DurationCalculator(BaseTool):
    """时间间隔计算工具"""

    name: str = "duration_calculator"
    description: str = (
        "计算两个时间点之间的时间间隔【而不是时间范围】。输入：时间间隔（秒）。输出：按秒、分钟、小时计算的时间间隔。"
    )
    input: str = "两个时间点（起始时间、结束时间）"
    output: str = "按秒、分钟、小时计算的时间间隔。"
    notices: List[str] = [
        "【不能用于计算时间范围】仅用于计算两个时间点之间的时间间隔。",
    ]
    parameters: dict = {
        "type": "object",
        "properties": {
            "start_time": {
                "type": "string",
                "description": "起始时间，格式为 'YYYY-MM-DD HH:MM:SS'。",
            },
            "end_time": {
                "type": "string",
                "description": "结束时间，格式为 'YYYY-MM-DD HH:MM:SS'。",
            },
        },
        "required": ["start_time", "end_time"],
    }

    def execute(self, start_time: str, end_time: str) -> ToolResult:
        """
        计算两个时间点之间的时间间隔。

        :param start_time (str): 起始时间，格式为 'YYYY-MM-DD HH:MM:SS'。
        :param end_time (str): 结束时间，格式为 'YYYY-MM-DD HH:MM:SS'。

        :return ToolResult: 计算得到的时间间隔
        """

        try:
            fmt = "%Y-%m-%d %H:%M:%S"
            start_dt = datetime.strptime(start_time, fmt)
            end_dt = datetime.strptime(end_time, fmt)

            seconds = (end_dt - start_dt).total_seconds()
            return ToolResult(
                output={
                    "result": TimeConverter().execute(seconds).output,
                    "range": (
                        "时间范围为{}到{}".format(start_time, end_time)
                        if seconds > 0
                        else "时间范围为{}到{}".format(end_time, start_time)
                    ),
                    "desc": (
                        f"{start_time}在{end_time}之前"
                        if seconds > 0
                        else f"{start_time}在{end_time}之后"
                    ),
                },
                
            )
        except Exception as e:
            return ToolFailure(error=f"时间格式错误或无效输入: {e}")
