# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from typing import List
import pandas as pd
from tool.base import BaseTool, ToolFailure, ToolResult


class KeyActionRetriever(BaseTool):
    """关键动作查询工具"""

    name: str = "key_action_retriever"
    description: str = (
        "查询某时间段（某设备）发生的所有关键动作。输入：起始时间、结束时间。输出：指定时间范围内发生的所有关键动作及其对应的设备。"
    )
    input: str = "起始时间、结束时间。"
    output: str = "指定时间范围内发生的所有关键动作及其对应的设备。"
    examples: List[str] = ["查询2023年8月10日上午什么设备进行了什么动作。"]
    notices: List[str] = [
        "查询（某设备在）某时间点发生的具体动作时，使用 key_action_retriever 函数，如查询浮标在2023年8月10日上午进行了什么动作",
        "查询某具体动作发生的时间点时，使用 data_filter 函数，如查询2023年5月1日浮标上浮的时间点",
    ]
    parameters: dict = {
        "type": "object",
        "properties": {
            "start_time": {
                "type": "string",
                "format": "date-time",
                "description": "查询的开始时间，格式为 'YYYY-MM-DD HH:MM:SS'，例如 '2024-08-23 00:00:00'。",
            },
            "end_time": {
                "type": "string",
                "format": "date-time",
                "description": "查询的结束时间，格式为 'YYYY-MM-DD HH:MM:SS'，例如 '2024-08-23 12:00:00'。",
            },
        },
        "required": ["start_time", "end_time"],
    }

    def execute(self, start_time: str, end_time: str):
        """
        根据开始时间和结束时间，查询什么设备在进行什么动作。返回正在进行的设备动作列表。

        :param start_time (str): 开始时间，格式为 'YYYY-MM-DD HH:MM:SS'
        :param end_time (str): 结束时间，格式为 'YYYY-MM-DD HH:MM:SS'

        :return dict: 包含设备状态变化的时间点和对应状态的字典，或错误信息
        """
        # 确保两个时间的差值至少是一分钟，如果小于一分钟，则end_time为start_time后一分钟
        start_time = start_time.replace("24:00:00", "23:59:59")
        end_time = end_time.replace("24:00:00", "23:59:59")

        start_time_dt = pd.to_datetime(start_time)
        end_time_dt = pd.to_datetime(end_time)
        if (end_time_dt - start_time_dt).total_seconds() < 60:
            end_time_dt = start_time_dt + pd.Timedelta(minutes=1)

        def get_status_changes(table_name, device_name):
            """
            辅助函数：获取指定设备在指定时间范围内的状态变化。

            参数:
            table_name (str): 数据表名
            device_name (str): 设备名称

            返回:
            dict: 包含设备状态变化的时间点和对应状态的字典，或错误信息
            """
            metadata = {
                "table_name": table_name,
                "start_time": start_time,
                "end_time": end_time,
            }

            try:
                df = pd.read_csv(f"{self.table_base_path}/{table_name}.csv")
            except FileNotFoundError:
                return ToolFailure(error=f"数据表 {table_name} 不存在")

            df["csvTime"] = pd.to_datetime(df["csvTime"], unit="ns")

            filtered_data = df[
                (df["csvTime"] >= start_time_dt)
                & (df["csvTime"] <= end_time_dt)
                & (df["key_action"] != "False")
            ]

            if filtered_data.empty:
                return ToolFailure(
                    error=f"在数据表 {table_name} 中未找到时间范围 {start_time} 到 {end_time} 且 key_action 不为 'False' 的数据",
                )
            if "key_action" not in filtered_data.columns:
                return ToolFailure(
                    error=f"数据表 {table_name} 中不存在 'key_action' 列",
                )

            status_changes = filtered_data[["csvTime", "key_action"]].copy()
            if device_name == "A架":
                status_changes = status_changes[
                    ~status_changes["key_action"].isin(["缆绳挂妥", "缆绳解除"])
                ]
            elif device_name == "绞车":
                status_changes = status_changes[
                    status_changes["key_action"].isin(["缆绳挂妥", "缆绳解除"])
                ]
            status_changes["csvTime"] = status_changes["csvTime"].dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            return ToolResult(
                output={
                    "设备名称": device_name,
                    "正在进行的关键动作": status_changes.to_dict(orient="records"),
                },
            )

        result1 = get_status_changes("A架动作表", "A架")
        result2 = get_status_changes("折臂吊车与小艇动作表", "折臂吊车")
        result3 = get_status_changes("艏侧推系统DP动作表", "艏推DP")
        result4 = get_status_changes("A架动作表", "绞车")

        results = [
            result.output
            for result in [result1, result2, result3, result4]
            if not isinstance(result, ToolFailure)
        ]

        return ToolResult(
            output={
                "results": results,
            },
        )
