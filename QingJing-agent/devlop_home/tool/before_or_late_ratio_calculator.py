# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from datetime import datetime, timedelta
from typing import List
from tool.base import BaseTool, ToolFailure, ToolResult
from tool.data_filter import DataFilter
import logger

action_table_configs = {
    "A架开机": "A架动作表",
    "ON DP": "艏侧推系统DP动作表",
    "征服者起吊": "A架动作表",
    "征服者入水": "A架动作表",
    "缆绳解除": "A架动作表",
    "A架摆回": "A架动作表",
    "小艇落座": "折臂吊车与小艇动作表",
    "A架关机": "A架动作表",
    "OFF DP": "艏侧推系统DP动作表",
    "折臂吊车开机": "折臂吊车与小艇动作表",
    "A架摆出": "A架动作表",
    "小艇检查完毕": "折臂吊车与小艇动作表",
    "小艇入水": "折臂吊车与小艇动作表",
    "缆绳挂妥": "A架动作表",
    "征服者出水": "A架动作表",
    "折臂吊车关机": "折臂吊车与小艇动作表",
    "征服者落座": "A架动作表",
}

action_field_configs = {
    "A架开机": ["Ajia-3_v", "Ajia-5_v"],
    "ON DP": ["P3_33", "P3_18"],
    "征服者起吊": ["Ajia-3_v", "Ajia-5_v"],
    "征服者入水": ["Ajia-3_v", "Ajia-5_v"],
    "缆绳解除": ["Ajia-3_v", "Ajia-5_v"],
    "A架摆回": ["Ajia-3_v", "Ajia-5_v"],
    "小艇落座": ["13-11-6_v"],
    "A架关机": ["Ajia-3_v", "Ajia-5_v"],
    "OFF DP": ["P3_33", "P3_18"],
    "折臂吊车开机": ["13-11-6_v"],
    "A架摆出": ["Ajia-3_v", "Ajia-5_v"],
    "小艇检查完毕": ["13-11-6_v"],
    "小艇入水": ["13-11-6_v"],
    "缆绳挂妥": ["Ajia-3_v", "Ajia-5_v"],
    "征服者出水": ["Ajia-3_v", "Ajia-5_v"],
    "折臂吊车关机": ["13-11-6_v"],
    "征服者落座": ["Ajia-3_v", "Ajia-5_v"],
}

action_rule_configs = {
    "A架开机": "电流值从error变为0（取0）",
    "ON DP": "数值从0增加（取增加）",
    "征服者起吊": "电流从稳定值（50多），取高于50的点",
    "征服者入水": "缆绳解除的时间点往前推一分钟",
    "缆绳解除": "电流从高值回落至稳定值（50多），取50",
    "A架摆回": "征服者入水后，电流重新增加到峰值（最大值点）",
    "小艇落座": "数值增加（回落前的最后一个值）",
    "A架关机": "电流值变为error（取error）",
    "OFF DP": "数值归零（取0）",
    "折臂吊车开机": "数值从0增加（取增加）",
    "A架摆出": "征服者起吊前，电流到达峰值（取峰值）",
    "小艇检查完毕": "数值增加（回落前的最后一个值）",
    "小艇入水": "数值增加（回落前的最后一个值）",
    "缆绳挂妥": "征服者出水往前推一分钟",
    "征服者出水": "电流峰值（取峰值）",
    "折臂吊车关机": "数值归零（取0）",
    "征服者落座": "电流从高值回落至稳定值（50多）（取50）",
}


class BeforeOrLateRatioCalculator(BaseTool):
    """早于/晚于比例计算工具"""

    name: str = "before_or_late_ratio_calculator"
    description: str = (
        "计算指定时间段内指定动作早于/晚于指定时间点发生的比例，返回值为百分比。示例问题：统计2024/8/24在9点前开始作业的比例"
    )
    input: str = "起始日期、结束日期、指定动作、指定时间点、指定早于/晚于"
    output: str = "指定时间段内指定动作早于/晚于指定时间点发生的比例，返回值为百分比。"
    examples: List[str] = [
        "统计2024/8/24在9点前征服者出水的比例",
    ]
    notices: List[str] = [
        "【任务分解】支持直接查询比例，如查询8月期间'浮标'每天9点前下沉的比例时，不需要统计每天9点前下沉的次数与下沉总次数，可直接查询比例",
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
            "key_action": {
                "type": "string",
                "description": "需要计算比例的动作名称，支持以下值：A架开机、ON DP、征服者起吊、征服者入水、缆绳解除、A架摆回、小艇落座、A架关机、OFF DP、折臂吊车开机、A架摆出、小艇检查完毕、小艇入水、缆绳挂妥、征服者出水、折臂吊车关机、征服者落座",
            },
            "time_point": {
                "type": "string",
                "description": "指定时间点，格式为 'HH:MM'，表示该时间点前的比例。",
            },
            "before_or_late": {
                "type": "string",
                "enum": ["早于", "晚于"],
                "description": "指定早于或晚于，可选值为'早于'、'晚于'",
            },
        },
        "required": [
            "start_date",
            "end_date",
            "key_action",
            "time_point",
            "before_or_late",
        ],
    }

    def execute(
        self,
        start_date: str,
        end_date: str,
        key_action: str,
        time_point: str,
        before_or_late: str,
    ) -> ToolResult:
        """
        计算指定时间段内指定动作早于/晚于指定时间点发生的比例

        :param start_time (str): 时间段的起始时间，格式为 'YYYY-MM-DD'
        :param end_time (str): 时间段的结束时间，格式为 'YYYY-MM-DD'
        :param action (str): 需要计算比例的动作名称，如 '起吊'、'入水' 等
        :param time_point (str): 指定时间点，格式为 'HH:MM'
        :param before_or_late (str): 早于或晚于，可选'早于'、'晚于'

        :return ToolResult: 动作早于/晚于指定时间点发生的比例，返回百分比
        """
        

        start_date = f"{start_date} 00:00:00"
        end_date = f"{end_date} 23:59:59"

        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        current_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

        time_point_dt = datetime.strptime(time_point, "%H:%M")
        time_point_dt = time_point_dt.replace(
            year=start_dt.year, month=start_dt.month, day=start_dt.day
        )

        if key_action not in action_table_configs.keys():
            return {
                "error": f"动作 {key_action} 不存在",
            }

        get_data_result = DataFilter.execute(
            action_table_configs[key_action],
            start_date,
            end_date,
            columns=["csvTime"],
            conditions=[{"column": "key_action", "operator": "==", "value": key_action}],
        )

        try:
            logger.info("【before_or_late_ratio中间结果】", get_data_result)
            table_data = get_data_result["result"]
        except:
            return {
                "result": 0,
                "unit": "%",
            }

        satisfy_count = 0
        total_count = 0
        day_map = {}
        
        while current_dt <= end_dt:
            day_str = current_dt.strftime("%Y-%m-%d")
            day_map[day_str] = {
                    "performed": True,
                    "filtered": False,
                }
            current_dt += timedelta(days=1)
        
        for res_time in table_data["csvTime"]:
            res_time_dt = datetime.strptime(res_time, "%Y-%m-%d %H:%M:%S")
            res_day = datetime.strftime(res_time_dt, "%Y-%m-%d")

            time_point_dt = time_point_dt.replace(
                year=res_time_dt.year, month=res_time_dt.month, day=res_time_dt.day
            )
            if before_or_late == "早于" and res_time_dt < time_point_dt:
                day_map[res_day] = {
                    "performed": True,
                    "filtered": True,
                }
            elif before_or_late == "晚于" and res_time_dt > time_point_dt:
                day_map[res_day] = {
                    "performed": True,
                    "filtered": True,
                }
            elif before_or_late not in ["早于", "晚于"]:
                return {
                    "error": "before_or_late可选值为'早于'、'晚于'",
                }

        for key in day_map:
            if day_map[key]["filtered"]:
                satisfy_count += 1

        total_count = len(day_map)

        if total_count == 0:
            proportion = 0
        else:
            proportion = (satisfy_count / total_count) * 100
        return {
            "result": proportion,
            "unit": "%"
        }
       