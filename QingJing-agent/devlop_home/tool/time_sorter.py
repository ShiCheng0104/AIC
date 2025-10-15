# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from datetime import datetime
import traceback
from typing import Dict, List
from tool.base import BaseTool, ToolFailure, ToolResult
import logger


class TimeSorter(BaseTool):
    """时间排序工具"""

    name: str = "time_sorter"
    description: str = (
        "对日期时间列表**仅按照时间（HH:MM:SS）进行排序**。输入：需要排序时间的列表，元素为日期字符串（格式为 'YYYY-MM-DD HH:MM:SS'）。输出：排序后的日期时间列表。支持升序或降序，支持筛选某每天时间点之前或之后。"
    )
    input: str = (
        "需要排序时间的列表，元素为日期字符串（格式为 'YYYY-MM-DD HH:MM:SS'）；对日期时间列表**仅按照时间（HH:MM:SS）进行排序**，支持升序或降序，支持筛选某每天时间点之前或之后。"
    )
    output: str = "排序后的日期时间列表。"
    examples: List[str] = [
        "筛选出10:00之前的时间并按时间升序排序：'2022-01-01 10:00:00', '2022-01-01 09:00:00', '2022-01-01 11:00:00'",
    ]
    notices: List[str] = [
        "若仅比较日期时间中时间字段（HH:MM:SS）的先后顺序时，或筛选某时间点之前或之后的日期时间，必须使用 time_sorter 函数",
    ]
    parameters: dict = {
        "type": "object",
        "properties": {
            "input_list": {
                "type": "array",
                "items": {"format": "date-time", "type": "string"},
                "description": "需要排序的列表，元素为日期字符串（格式为 'YYYY-MM-DD HH:MM:SS'）。",
            },
            "order": {
                "type": "string",
                "enum": ["asc", "desc"],
                "description": "排序方式，'asc' 表示升序，'desc' 表示降序。",
            },
            "conditions_logic": {
                "type": "string",
                "enum": ["AND", "OR"],
                "default": "AND",
                "description": "逻辑运算符，可选 'AND' 或 'OR'，用于组合多个条件。",
            },
            "conditions": {
                "type": "array",
                "description": "可用于筛选指定时间段内的项，如筛选每天12:00前的时间。",
                "items": {
                    "type": "object",
                    "properties": {
                        "operator": {
                            "type": "string",
                            "enum": ["in", "==", ">", "<", ">=", "<=", "!="],
                            "description": "运算符，支持以下值：'in', '==', '>', '<', '>=', '<=', '!='。",
                        },
                        "value": {
                            "type": "string",
                            "description": "用于过滤的值，为日期字符串（格式为 'HH:MM:SS'）。如果运算符为in，value为以逗号分隔的字符串列表（示例：value1,value2,value3）",
                        },
                    },
                    "required": ["operator", "value"],
                },
            },
        },
        "required": ["input_list", "order"],
    }

    def execute(
        self,
        input_list: List[str],
        order: str,
        conditions_logic: str = "AND",
        conditions: List[Dict[str, str]] = None,
    ) -> ToolResult:
        """
        对日期时间列表仅按时间（格式为 'HH:MM:SS'）进行排序，支持升序或降序。

        :param input_list (list[str]): 需要排序的列表，元素必须是日期字符串（格式为 'YYYY-MM-DD HH:MM:SS'）。
        :param order (str): 排序方式，'asc' 表示升序，'desc' 表示降序。
        :param conditions_logic (str): 过滤条件逻辑，支持AND、OR。
        :param conditions (List[Dict[str, str]], 可选): 过滤条件，每个条件包含：
                - "operator": 过滤操作符（in, ==, >, <, >=, <=, !=）
                - "value": 过滤值

        :return ToolResult: 排序后的列表及相关信息。
        """
        try:

            def parse_value_date(value):
                """解析日期时间字符串，提取时间部分"""
                dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                return dt.time()

            def parse_value_time(value):
                """解析时间字符串"""
                return datetime.strptime(value, "%H:%M:%S").time()

            sorted_list = sorted(
                input_list, key=parse_value_date, reverse=(order == "desc")
            )

            if conditions:
                logic = conditions_logic.upper()
                if logic not in ["AND", "OR"]:
                    return ToolFailure(
                        error=f"不支持的逻辑操作符: {logic}"
                    )

                mask = (
                    [False] * len(sorted_list)
                    if logic == "OR"
                    else [True] * len(sorted_list)
                )

                for condition in conditions:
                    operator, value = (
                        condition["operator"],
                        condition["value"],
                    )
                    if operator not in ["in", "==", ">", "<", ">=", "<=", "!="]:
                        return ToolFailure(
                            error=f"不支持的操作符: {operator}"
                        )
                    try:
                        parsed_value = parse_value_time(value)
                    except ValueError as e:
                        return ToolFailure(error=str(e))

                    condition_mask = []
                    for item in sorted_list:
                        try:
                            parsed_item = parse_value_date(item)
                        except ValueError:
                            condition_mask.append(False)
                            continue

                        if operator == "==":
                            condition_mask.append(parsed_item == parsed_value)
                        elif operator == "!=":
                            condition_mask.append(parsed_item != parsed_value)
                        elif operator == ">":
                            condition_mask.append(parsed_item > parsed_value)
                        elif operator == "<":
                            condition_mask.append(parsed_item < parsed_value)
                        elif operator == ">=":
                            condition_mask.append(parsed_item >= parsed_value)
                        elif operator == "<=":
                            condition_mask.append(parsed_item <= parsed_value)
                        elif operator == "in":
                            if isinstance(value, str):
                                value_list = [
                                    parse_value_time(v.strip())
                                    for v in value.split(",")
                                ]
                            else:
                                return ToolFailure(
                                    error=f"条件值 {value} 格式错误，in 操作符需要以逗号分隔的字符串",
                                    
                                )
                            condition_mask.append(parsed_item in value_list)

                    if logic == "AND":
                        mask = [m1 & m2 for m1, m2 in zip(mask, condition_mask)]
                    else:
                        mask = [m1 | m2 for m1, m2 in zip(mask, condition_mask)]

                sorted_list = [item for item, keep in zip(sorted_list, mask) if keep]

            dates = sorted(
                {
                    datetime.strptime(x, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                    for x in sorted_list
                }
            )
            return ToolResult(
                output={
                    "result": sorted_list,
                    "filted_dates": f"符合筛选条件的所有日期：{dates}",
                    "desc": f"列表已按时间进行 {'升序' if order == 'asc' else '降序'} 排序；并返回",
                },
                
            )
        except ValueError as e:
            return ToolFailure(error=f"排序失败: {e}")
