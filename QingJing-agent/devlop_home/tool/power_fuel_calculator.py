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


class PowerFuelCalculator(BaseTool):
    """发电机发电量/燃油消耗量计算工具"""

    name: str = "power_fuel_calculator"
    description: str = (
        "计算发电机的发电量或燃油消耗量。输入：起始时间、结束时间、设备名称（如一号/二号/三号/四号或整个柴油发电机组）、查询类型（**理论发电量**、实际发电量、燃油消耗量）。输出：指定设备在指定时间范围内的理论发电量（单位：kWh）或实际发电量（单位：kWh）或燃油消耗量（单位：L）。"
    )
    input: str = (
        "起始时间、结束时间、设备名称（如一号/二号/三号/四号或整个柴油发电机组）、查询类型（**理论发电量**、实际发电量、燃油消耗量）。"
    )
    output: str = (
        "指定设备在指定时间范围内的理论发电量（单位：**kWh**）或实际发电量（单位：kWh）或燃油消耗量（单位：L）。"
    )
    notices: List[str] = [
        "【任务分解】计算理论发电量时直接使用 power_fuel_calculator 函数，而非先计算燃油消耗量",
        "【任务分解】计算理论发电量时，返回的单位即为 kWh，无需与 MJ 进行转换，不要冗余拆分",
        "多组设备时，优先使用合适的设备名称参数一次计算总值，如查询1~4号柴油发电机组的理论发电量，可以直接查询'整个柴油发电机组'的理论发电量",
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
            "type": {
                "type": "string",
                "description": "查询的类型，支持以下值：'理论发电量'、'实际发电量'、'燃油消耗量'。",
                "enum": ["理论发电量", "实际发电量", "燃油消耗量"],
            },
            "device_name": {
                "type": "string",
                "description": "设备名称，支持以下值：'一号柴油发电机'、'二号柴油发电机'、'三号柴油发电机'、'四号柴油发电机'、'整个柴油发电机组'。",
                "enum": [
                    "一号柴油发电机",
                    "二号柴油发电机",
                    "三号柴油发电机",
                    "四号柴油发电机",
                    "整个柴油发电机组",
                ],
            },
            "diesel_density": {
                "type": "number",
                "description": "柴油密度，单位 kg/L。当 type 为 '理论发电量' 时提供。",
            },
            "diesel_calorific_value": {
                "type": "number",
                "description": "柴油热值，单位 MJ/kg。当 type 为 '理论发电量' 时提供。",
            },
        },
        "required": ["start_time", "end_time", "type", "device_name"],
    }

    def execute(
        self,
        start_time: str,
        end_time: str,
        type: str,
        device_name: str,
        diesel_density: float = None,
        diesel_calorific_value: float = None,
    ) -> ToolResult:
        """
        根据开始时间和结束时间，查询设备在指定时间范围内的发电量或燃油消耗量

        :param start_time (str): 查询的开始时间（字符串类型）
        :param end_time (str): 查询的结束时间（字符串类型）
        :param type (str): 查询类型，'理论发电量'、'实际发电量'、'燃油消耗量'
        :param device_name (str): 设备名称，'一号柴油发电机'、'二号柴油发电机'、'三号柴油发电机'、'四号柴油发电机'、'整个柴油发电机组'
        :param diesel_density (float): 柴油密度，单位kg/L
        :param diesel_calorific_value (float): 柴油热值，单位MJ/kg
        :return ToolResult: 发电量或燃油消耗量
        """
        device_config = {
            "燃油消耗量": {
                "一号柴油发电机": ("Port1_ksbg_1", "P1_3"),
                "二号柴油发电机": ("Port1_ksbg_1", "P1_25"),
                "三号柴油发电机": ("Port2_ksbg_1", "P2_3"),
                "四号柴油发电机": ("Port2_ksbg_1", "P2_25"),
                "整个柴油发电机组": [
                    "一号柴油发电机",
                    "二号柴油发电机",
                    "三号柴油发电机",
                    "四号柴油发电机",
                ],
            },
            "实际发电量": {
                "一号柴油发电机": ("Port1_ksbg_3", "P1_66"),
                "二号柴油发电机": ("Port1_ksbg_3", "P1_75"),
                "三号柴油发电机": ("Port2_ksbg_2", "P2_51"),
                "四号柴油发电机": ("Port2_ksbg_3", "P2_60"),
                "整个柴油发电机组": [
                    "一号柴油发电机",
                    "二号柴油发电机",
                    "三号柴油发电机",
                    "四号柴油发电机",
                ],
            },
            "理论发电量": {
                "一号柴油发电机": ("Port1_ksbg_1", "P1_3"),
                "二号柴油发电机": ("Port1_ksbg_1", "P1_25"),
                "三号柴油发电机": ("Port2_ksbg_1", "P2_3"),
                "四号柴油发电机": ("Port2_ksbg_1", "P2_25"),
                "整个柴油发电机组": [
                    "一号柴油发电机",
                    "二号柴油发电机",
                    "三号柴油发电机",
                    "四号柴油发电机",
                ],
            },
        }

        if type not in device_config.keys():
            return ToolFailure(error=f"未知的类型: {type}")

        if device_name not in device_config[type].keys():
            return ToolFailure(error=f"未知的设备名称: {device_name}")

        if type == "理论发电量" and (
            diesel_density is None or diesel_calorific_value is None
        ):
            return ToolFailure(error=f"柴油密度或柴油热值不能为None")

        result = None
        if isinstance(device_config[type][device_name], list):
            total_energy = 0
            for sub_device in device_config[type][device_name]:
                try:
                    energy = self.execute(
                        start_time,
                        end_time,
                        type,
                        sub_device,
                        diesel_density,
                        diesel_calorific_value,
                    ).output["result"]
                    if energy is not None:
                        total_energy += energy
                except Exception as e:
                    logger.error(
                        f"计算设备 {sub_device} {type}时出错: {traceback.format_exc()}"
                    )
            result = total_energy
        else:
            file_name, field_name = device_config[type][device_name]
            file_path = f"{self.table_base_path}/{file_name}.csv"
            try:
                filtered_data = load_and_filter_data(
                    file_path, start_time, end_time, field_name
                )
                if isinstance(filtered_data, str) or filtered_data is None:
                    result = None
                else:
                    total_energy_kWh = filtered_data["energy_kWh"].sum()
                    if type == "理论发电量":
                        result = (
                            total_energy_kWh
                            * diesel_density
                            * diesel_calorific_value
                            / 3.6
                        )
                    else:
                        result = total_energy_kWh

            except Exception as e:
                logger.error(
                    f"计算设备 {device_name} {type}时出错: {traceback.format_exc()}"
                )
        return ToolResult(
            output={
                "result": result,
                "unit": "L" if type == "燃油消耗量" else "kWh",
            },
            
        )
