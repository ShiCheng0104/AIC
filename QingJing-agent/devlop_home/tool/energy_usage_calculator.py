# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import traceback
from typing import List
import pandas as pd
from tool.base import BaseTool, ToolFailure, ToolResult
from texttable import Texttable
from utils import load_and_filter_data
import logger


class EnergyUsageCalculator(BaseTool):
    """设备能耗/做功计算工具"""

    name: str = "energy_usage_calculator"
    description: str = (
        "计算设备的总能耗（总做功）。输入：起始时间、结束时间、设备名称。输出：该设备在指定时间范围内的总能耗或总做功（单位：kWh）。支持的设备包括：'全船'、'甲板机械设备'（包括折臂吊车、门架、绞车等）、'A架'、'折臂吊车'、'一号门架'、'二号门架'、'绞车变频器'、'推进系统'（推进器）、'主推'（主推进器）、'一号推进变频器'、'二号推进变频器'、'可伸缩推'、'侧推'、'舵桨'（整体舵桨系统）、'一号舵桨转舵A'、'一号舵桨转舵B'、'二号舵桨转舵A'、'二号舵桨转舵B'"
    )
    input: str = (
        "起始时间、结束时间、设备名称（如全船、甲板机械设备、推进系统、折臂吊车、舵桨等）。"
    )
    output: str = "该设备在指定时间范围内的总能耗或总做功（单位：kWh）。"
    notices: List[str] = ["如涉及多组设备的能耗计算，优先使用设备名称参数一次计算总值"]
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
            "device_name": {
                "type": "string",
                "description": "设备名称，支持以下值：'全船'、'甲板机械设备'（包括折臂吊车、门架、绞车等）、'A架'、'折臂吊车'、'一号门架'、'二号门架'、'绞车变频器'、'推进系统'（又称推进器，包括主推进器、可伸缩推、侧推）、'主推'（主推进器，包含一/二号推进变频器）、''一号推进变频器'、'二号推进变频器'、'可伸缩推'、'侧推'、'舵桨'（整体舵桨系统）、'一号舵桨转舵A'、'一号舵桨转舵B'、'二号舵桨转舵A'、'二号舵桨转舵B'。",
                "enum": [
                    "全船",
                    "甲板机械设备",
                    "折臂吊车",
                    "A架",
                    "一号门架",
                    "二号门架",
                    "绞车变频器",
                    "推进系统",
                    "主推",
                    "一号推进变频器",
                    "二号推进变频器",
                    "可伸缩推",
                    "侧推",
                    "舵桨",
                    "一号舵桨转舵A",
                    "一号舵桨转舵B",
                    "二号舵桨转舵A",
                    "二号舵桨转舵B",
                ],
            },
        },
        "required": ["start_time", "end_time", "device_name"],
    }

    def execute(self, start_time: str, end_time: str, device_name: str) -> ToolResult:
        """
        根据开始时间和结束时间，查询设备在指定时间范围内的总能耗。

        :param start_time (str): 查询的开始时间
        :param end_time (str): 查询的结束时间
        :param device_name (str): 设备名称，默认为 '折臂吊车'

        :return ToolResult: 总能耗（kWh，float 类型）
        """
        start_time = start_time.replace("24:00:00", "23:59:59")
        end_time = end_time.replace("24:00:00", "23:59:59")

        device_config = {
            "全船": ["甲板机械设备", "推进系统", "舵桨"],
            "甲板机械设备": ["折臂吊车", "A架", "绞车变频器"],
            "折臂吊车": ("折臂吊车与小艇动作表", "13-11-6_v"),
            "A架": ["一号门架", "二号门架"],
            "一号门架": ("device_1_5_meter_105", "1-5-6_v"),
            "二号门架": ("device_13_14_meter_1314", "13-14-6_v"),
            "绞车变频器": ("device_1_15_meter_115", "1-15-8_v"),
            "推进系统": ["主推", "可伸缩推", "侧推"],
            "主推": ["一号推进变频器", "二号推进变频器"],
            "一号推进变频器": ("Port3_ksbg_8", "P3_15"),
            "二号推进变频器": ("Port4_ksbg_7", "P4_16"),
            "可伸缩推": ("Port4_ksbg_8", "P4_21"),
            "侧推": ("艏侧推系统DP动作表", "P3_18"),
            "舵桨": [
                "一号舵桨转舵A",
                "一号舵桨转舵B",
                "二号舵桨转舵A",
                "二号舵桨转舵B",
            ],
            "一号舵桨转舵A": ("device_1_2_meter_102", "1-2-6_v"),
            "一号舵桨转舵B": ("device_1_3_meter_103", "1-3-6_v"),
            "二号舵桨转舵A": ("device_13_2_meter_1302", "13-2-6_v"),
            "二号舵桨转舵B": ("device_13_3_meter_1303", "13-3-6_v"),
        }
        if device_name not in device_config.keys():
            return ToolFailure(error=f"未知的设备名称: {device_name}")

        result = None
        if isinstance(device_config[device_name], list):
            total_energy = 0
            for sub_device in device_config[device_name]:
                try:
                    energy = self.execute(
                        start_time, end_time, device_name=sub_device
                    ).output["result"]
                    if energy:
                        total_energy += energy
                except Exception as e:
                    logger.error(
                        f"计算设备 {sub_device} 能耗时出错: {e},{traceback.format_exc()}"
                    )
            result = total_energy
        else:
            table_name, power_column = device_config[device_name]
            file_path = f"{self.table_base_path}/{table_name}.csv"
            try:
                filtered_data = load_and_filter_data(
                    file_path, start_time, end_time, power_column
                )
                if isinstance(filtered_data, str) or filtered_data is None:
                    result = None
                else:
                    total_energy_kWh = filtered_data["energy_kWh"].sum()
                    result = total_energy_kWh
            except Exception as e:
                logger.error(
                    f"计算设备 {device_name} 能耗时出错: {e},{traceback.format_exc()}"
                )
        return ToolResult(
            output={
                "result": result,
                "unit": "kWh",
            },
            
        )
