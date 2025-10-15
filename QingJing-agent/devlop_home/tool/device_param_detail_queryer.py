# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from typing import List
import pandas as pd
from tool.base import BaseTool, ToolFailure, ToolResult
from texttable import Texttable
import logger


class DeviceParamDetailQueryer(BaseTool):
    """设备参数详情查询工具"""

    name: str = "device_param_detail_queryer"
    description: str = (
        "查询设备参数信息。输入：设备参数的中文名称。输出：该参数的上下限范围及触发的机制（如报警值、安全保护设定值及对应措施）及其他信息。"
    )
    input: str = "设备参数的中文名称（列表，支持一次查询多个参数）。"
    output: str = (
        "输入中所有参数的上下限范围及触发的机制（如报警值、安全保护设定值及对应措施）。"
    )
    notices: List[str] = ["【任务分解】查询多个参数的信息时，不要分解为多个步骤查询"]
    parameters: dict = {
        "type": "object",
        "properties": {
            "params": {
                "type": "array",
                "description": "设备参数名称列表",
                "items": {
                    "type": "string",
                    "description": "参数中文名，用于查询设备参数信息。",
                },
            }
        },
        "required": ["params"],
    }

    def get_single_device_parameter_detail(self, parameter_name_cn: str):
        """
        根据设备名，查询设备的参数值。
        :param device_name: 参数中文名
        :return: 返回包含参数信息的字典
        """

        df = pd.read_csv(f"{self.table_base_path}/设备参数详情.csv")
        if not df["Channel_Text_CN"].str.contains(parameter_name_cn).any():
            return ToolFailure(
                error=f"未找到包含 '{parameter_name_cn}' 的参数中文名"
            )

        parameter_info = df[df["Channel_Text_CN"].str.contains(parameter_name_cn)].iloc[
            0
        ]

        parameter_dict = {
            "参数名": parameter_info["Channel_Text"],
            "参数中文名": parameter_info["Channel_Text_CN"],
            "参数下限": parameter_info["Alarm_Information_Range_Low"],
            "参数上限": parameter_info["Alarm_Information_Range_High"],
            "报警值的单位": parameter_info["Alarm_Information_Unit"],
            "报警值": parameter_info["Parameter_Information_Alarm"],
            "屏蔽值": parameter_info["Parameter_Information_Inhibit"],
            "延迟值": parameter_info["Parameter_Information_Delayed"],
            "安全保护设定值": parameter_info["Safety_Protection_Set_Value"],
            "附注（达到安全保护设定值时的措施）": parameter_info["Remarks"],
        }

        parameter_dict = {
            key: (None if pd.isna(value) else value)
            for key, value in parameter_dict.items()
        }

        for key, value in parameter_dict.items():
            str_value = str(value).strip()
            if "↑" in str_value:
                parameter_dict[key] = "若超过 " + str_value.replace("↑", " 则触发 ")
            if "↓" in str_value:
                parameter_dict[key] = "若低于 " + str_value.replace("↓", " 则触发 ")

        if (
            parameter_dict["安全保护设定值"] is not None
            and parameter_info["Remarks"] is not None
        ):
            parameter_dict["安全保护设定值"] += parameter_info["Remarks"]
        if parameter_dict["报警值"] is not None:
            parameter_dict["报警值"] += "报警"

        return ToolResult(output=parameter_dict)

    def execute(self, params: list[str]) -> ToolResult:
        """
        根据设备名，查询设备的参数值。

        :param device_name (list[str]): 参数中文名

        :return ToolResult: 返回包含参数信息的字典
        """

        details = []
        for param in params:
            details.append(self.get_single_device_parameter_detail(param))

        table = Texttable()
        table.set_deco(Texttable.HEADER)
        table.set_cols_width([10, 1000])
        table.set_cols_align(["c", "c"])
        table.add_row(["参数名称", "参数详情"])
        for row in details:
            table.add_row([row["parameter_name_cn"], row["result"]])
        logger.debug("\n", table.draw())

        return ToolResult(
            output={
                "results": details,
            },
            
        )
