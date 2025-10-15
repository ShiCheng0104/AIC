# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from datetime import datetime
import traceback
from typing import Dict, List

import pandas as pd
from tool.base import BaseTool, ToolFailure, ToolResult
import logger


class DeepseaOperationCounter(BaseTool):
    """时间排序工具"""

    name: str = "deepsea_operation_counter"
    description: str = (
        "统计一段时间内完整深海作业的次数。输入：起始时间、结束时间。输出：在指定时间范围内进行的深海作业的次数。"
    )
    input: str = "起始时间、结束时间。"
    output: str = "在指定时间范围内进行的完整的深海作业次数。"
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

    def execute(self, start_time: str, end_time: str):
        """
        统计两个时间点之间的完整深海作业的次数。
        :param start_time: 开始时间
        :param end_time: 结束时间
        :return: 作业次数
        """
        # 确保两个时间的差值至少是一分钟，如果小于一分钟，则end_time为start_time后一分钟
        start_time = start_time.replace("24:00:00", "23:59:59")
        end_time = end_time.replace("24:00:00", "23:59:59")

        start_time_dt = pd.to_datetime(start_time)
        end_time_dt = pd.to_datetime(end_time)
        if (end_time_dt - start_time_dt).total_seconds() < 60:
            end_time_dt = start_time_dt + pd.Timedelta(minutes=1)
        df = pd.read_csv(f"{self.table_base_path}/A架动作表.csv")
        df["csvTime"] = pd.to_datetime(df["csvTime"])
        df = df[
            (df["csvTime"] >= start_time)
            & (df["csvTime"] <= end_time)
            & (df["stage"].isin(["布放阶段结束", "回收阶段开始"]))
        ]
        df = df.sort_values(by="csvTime")
        # 分离 `布放阶段结束` 和 `回收阶段开始`
        deploy_end_times = df[df["stage"] == "布放阶段结束"]["csvTime"].tolist()
        retrieve_start_times = df[df["stage"] == "回收阶段开始"]["csvTime"].tolist()

        count = 0
        j = 0  # `回收阶段开始` 的索引

        # 遍历 `布放阶段结束` 的时间点，匹配最近的 `回收阶段开始`
        for deploy_time in deploy_end_times:
            while (
                j < len(retrieve_start_times) and retrieve_start_times[j] < deploy_time
            ):
                j += 1  # 跳过早于当前 `布放阶段结束` 的 `回收阶段开始`

            if (
                j < len(retrieve_start_times)
                and (retrieve_start_times[j] - deploy_time).total_seconds() <= 12 * 3600
            ):
                count += 1
                j += 1  # 移动到下一个 `回收阶段开始`

        return ToolResult(output=count)
