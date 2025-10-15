# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from datetime import datetime, timedelta
import traceback
from typing import Dict, List
from tool.base import BaseTool, ToolFailure, ToolResult
from tool.data_aggregator import DataAggregator
from tool.data_filter import DataFilter
import logger


class SalingStageQueryer(BaseTool):
    """航行状态查询工具"""

    name: str = "saling_stage_queryer"
    description: str = (
        "计算指定时间段内每天指定航行状态的开始时间、结束时间和时长，支持'停泊状态'、'航渡状态'、'动力定位状态'、'伴航状态'"
    )
    input: str = "指定时间段，指定航行状态"
    output: str = (
        "查询指定时间段内**每一天**指定航行状态的开始时间、结束时间和时长，支持'停泊状态'、'航渡状态'、'动力定位状态'、'伴航状态'。"
    )
    examples: List[str] = [
        "统计2024/8/24-2024/8/25停泊状态的开始时间和时长",
    ]
    notices: List[str] = [
        "【任务分解】支持统计多天的数据，如涉及多天的航行状态统计，不要分解为多个步骤查询",
    ]
    parameters: dict = {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "description": "时间段起始日期，格式为 'YYYY-MM-DD'。",
            },
            "end_date": {
                "type": "string",
                "description": "时间段结束日期，格式为 'YYYY-MM-DD'。",
            },
            "stage": {
                "type": "string",
                "enum": ["停泊状态", "航渡状态", "动力定位状态", "伴航状态"],
                "description": "需要查询到航行状态，支持'停泊状态'、'航渡状态'、'动力定位状态'、'伴航状态'。",
            },
        },
        "required": ["start_date", "end_date", "stage"],
    }

    def execute(self, start_date: str, end_date: str, stage: str) -> ToolResult:
        """
        计算指定时间段内每天指定航行状态的开始时间、结束时间和时长。

        :param start_date (str): 时间段起始日期，格式为 'YYYY-MM-DD'
        :param end_date (str): 时间段结束日期，格式为 'YYYY-MM-DD'
        :param stage (str): 查询的航行状态，支持'停泊状态'、'航渡状态'、'动力定位状态'、'伴航状态'

        :return ToolResult: 每天的开始时间、结束时间和时长信息。
        """
        start_date = f"{start_date} 00:00:00"
        end_date = f"{end_date} 23:59:59"

        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        current_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

        stage_column_map = {
            "停泊状态": "docking_status",
            "航渡状态": "voyage_status",
            "动力定位状态": "dp_status",
            "伴航状态": "escort_status",
        }

        if stage not in stage_column_map:
            return ToolFailure(error=f"无效的航行状态: {stage}")

        data_filter_result = DataFilter().execute(
            "航行状态表",
            start_date,
            end_date,
            columns=["csvTime", stage_column_map[stage]],
            conditions=[
                {
                    "column": stage_column_map[stage],
                    "operator": "in",
                    "value": ",".join([f"{stage}开始", f"{stage}中", f"{stage}结束"]),
                }
            ],
            ignore_too_many=True,
        )

        try:
            filtered_data = data_filter_result.output["result"]
        except:
            return ToolFailure(
                error=f"获取数据错误: {data_filter_result.error}"
            )

        start_points = {}
        end_points = {}

        while current_dt <= end_dt:
            day_str = current_dt.strftime("%Y-%m-%d")
            start_points[day_str] = []
            end_points[day_str] = []
            current_dt += timedelta(days=1)

        for index, item in enumerate(filtered_data["csvTime"]):
            res_time = item
            res_stage = filtered_data[stage_column_map[stage]][index]
            res_time_dt = datetime.strptime(res_time, "%Y-%m-%d %H:%M:%S")
            res_day = datetime.strftime(res_time_dt, "%Y-%m-%d")

            if f"{stage}开始" in res_stage:
                start_points[res_day].append(res_time)
            elif f"{stage}结束" in res_stage:
                end_points[res_day].append(res_time)

        result = []
        for day in start_points.keys():
            data_aggregator_result = (
                DataAggregator()
                .execute(
                    "航行状态表",
                    f"{day} 00:00:00",
                    f"{day} 23:59:59",
                    stage_column_map[stage],
                    method="count",
                    conditions=[
                        {
                            "column": stage_column_map[stage],
                            "operator": "in",
                            "value": ",".join([f"{stage}开始", f"{stage}中"]),
                        }
                    ],
                )
                .output[f"{stage_column_map[stage]}_count"]
            )
            if data_aggregator_result > 0:
                if len(start_points.get(day, [])) == 0:
                    start_points[day].append(f"{day} 00:00:00")
                if len(end_points.get(day, [])) == 0:
                    end_points[day].append(f"{day} 23:59:59")
            sorted_start_points = sorted(start_points.get(day, []))
            sorted_end_points = sorted(end_points.get(day, []))
            duration = 0
            for start_time, end_time in zip(sorted_start_points, sorted_end_points):
                duration += round(
                    (
                        datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                        - datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                    ).total_seconds()
                    / 60
                )
            result.append(
                {
                    "日期": day,
                    "开始时间列表": start_points.get(day, []),
                    "结束时间列表": end_points.get(day, []),
                    f"{stage}总时长": f"{duration}分钟",
                }
            )

        return ToolResult(output=result)
