# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from typing import Dict, List

import pandas as pd
from tool.base import BaseTool, ToolFailure, ToolResult
from utils import get_table_meta, render_text_table
import logger


class DataFilter(BaseTool):
    """数据查询工具"""

    name: str = "data_filter"
    description: str = (
        "查询筛选后的数据。输入：数据表名、起始时间、结束时间、列名（可选）、过滤条件（可选）。输出：指定时间范围内符合过滤条件的数据。支持按关键动作筛选（如A架开机、ON DP、征服者起吊等），支持查询特定工作状态（布放、回收、开机运行中等）。"
    )
    input: str = (
        "数据表名、起始时间、结束时间、列名（可选）、过滤条件（可选）。支持按关键动作筛选（如A架开机、ON DP、征服者起吊等），支持查询特定工作状态（布放、回收、开机运行中等）。"
    )
    output: str = "指定时间范围内符合过滤条件的数据。"
    examples: List[str] = ["查询2023年5月1日浮标上浮的时间点"]
    parameters: dict = {
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "数据表名。"},
            "start_time": {
                "type": "string",
                "format": "date-time",
                "description": "查询的开始时间，格式为 'YYYY-MM-DD HH:MM:SS'，例如 '2024-08-23 00:00:00'。查询某个时间点的数据时，start_time=end_time，如查询2024年8月23日16点24的数据，start_time=end_time='2024-08-23 16:24:00'。",
            },
            "end_time": {
                "type": "string",
                "format": "date-time",
                "description": "查询的结束时间，格式为 'YYYY-MM-DD HH:MM:SS'，例如 '2024-08-23 12:00:00'。查询某个时间点的数据时，start_time=end_time，如查询2024年8月23日16点24的数据，start_time=end_time='2024-08-23 16:24:00'。",
            },
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "需要查询的列名列表。如果未提供，则返回所有列。请根据题目要求，尽可能精确地给出要查询的列",
                "default": [],
            },
            "conditions_logic": {
                "type": "string",
                "enum": ["AND", "OR"],
                "default": "AND",
                "description": "逻辑运算符，可选 'AND' 或 'OR'，用于组合多个条件，当需要进行多个条件的限制时选择'AND'，当需要筛选出满足任意一个条件的数据时选择'OR'。",
            },
            "conditions": {
                "type": "array",
                "description": "可选的过滤条件列表，每个条件包含列名、运算符和值。",
                "items": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "过滤条件的列名。"},
                        "operator": {
                            "type": "string",
                            "enum": ["in", "==", ">", "<", ">=", "<=", "!="],
                            "description": "运算符，支持以下值：'in','==', '>', '<', '>=', '<=', '!='。",
                        },
                        "value": {
                            "type": "string",
                            "description": "用于过滤的值，类型为字符串。如果运算符为in，value为以逗号分隔的字符串列表（示例：value1,value2,value3）",
                        },
                    },
                    "required": ["column", "operator", "value"],
                },
            },
        },
        "required": ["table_name", "start_time", "end_time", "columns"],
    }

    def execute(
        self,
        table_name: str,
        start_time: str,
        end_time: str,
        columns=None,
        conditions_logic: str = "AND",
        conditions: List[Dict[str, str]] = None,
        ignore_too_many: bool = False,
        max_length: int = 100,
    ):
        """
        根据数据表名、开始时间、结束时间、列名获取指定时间范围内的相关数据。返回值为包含指定列名和对应值的字典。

        :param table_name (str): 数据表名
        :param start_time (str): 开始时间，格式为 'YYYY-MM-DD HH:MM:SS'
        :param end_time (str): 结束时间，格式为 'YYYY-MM-DD HH:MM:SS'
        :param columns (list): 需要查询的列名列表，如果为None，则返回所有列
        :param conditions_logic (str): 过滤条件逻辑，支持AND、OR
        :param conditions (List[Dict[str, str]], 可选): 过滤条件，每个条件包含：
            - "column": 过滤列名
            - "operator": 过滤操作符（in, ==, >, <, >=, <=, !=）
            - "value": 过滤值
        :param max_length (int): 查询到的数据条数最大值
        :return dict: 包含指定列名和对应值的字典，或错误信息
        """
        try:
            df = pd.read_csv(f"{self.table_base_path}/{table_name}.csv")
        except FileNotFoundError:
            return ToolFailure(error=f"数据表 {table_name} 不存在")

        df["csvTime"] = pd.to_datetime(df["csvTime"], unit="ns")

        start_time = start_time.replace("24:00:00", "23:59:59")
        end_time = end_time.replace("24:00:00", "23:59:59")

        start_time = pd.to_datetime(start_time)
        end_time = pd.to_datetime(end_time)
        if (
            start_time.minute == end_time.minute
            and start_time.hour == end_time.hour
            and start_time.day == end_time.day
            and start_time.second != end_time.second
        ):
            start_time = start_time.replace(second=0)
            end_time = end_time.replace(second=59)

        if start_time == end_time:
            closest_data = df.iloc[(df["csvTime"] - start_time).abs().argsort()[:1]]
            if closest_data.empty:
                return ToolFailure(
                    error=f"在数据表 {table_name} 中未找到时间点 {start_time} 附近的数据",
                    
                )

            filtered_data = closest_data
        else:
            filtered_data = df[
                (df["csvTime"] >= start_time) & (df["csvTime"] <= end_time)
            ]

        if filtered_data.empty:
            return ToolFailure(
                error=f"在数据表 {table_name} 中未找到时间范围 {start_time} 到 {end_time} 的数据",
                
            )

        condition_columns = []
        if conditions:
            logic = conditions_logic.upper()
            if logic not in ["AND", "OR"]:
                return ToolFailure(
                    error=f"不支持的逻辑操作符: {logic}"
                )
            mask = None
            for condition in conditions:
                cond_col, operator, cond_value = (
                    condition["column"],
                    condition["operator"],
                    condition["value"],
                )
                if cond_col == "csvTime":
                    return ToolFailure(
                        error=f"过滤条件不支持'csvTime',请使用'start_time'和'end_time'",
                        
                    )
                condition_columns.append(cond_col)

                if cond_col not in filtered_data.columns:
                    return ToolFailure(
                        error=f"条件列 {cond_col} 不存在于数据表 {table_name}",
                        
                    )

                try:
                    cond_value = float(cond_value)
                    column_values = filtered_data[cond_col].astype(float)
                except ValueError:
                    cond_value = str(cond_value)
                    column_values = filtered_data[cond_col].astype(str)

                if operator == "==":
                    condition_mask = column_values == cond_value
                elif operator == "!=":
                    condition_mask = column_values != cond_value
                elif operator == ">":
                    condition_mask = column_values > cond_value
                elif operator == "<":
                    condition_mask = column_values < cond_value
                elif operator == ">=":
                    condition_mask = column_values >= cond_value
                elif operator == "<=":
                    condition_mask = column_values <= cond_value
                elif operator == "in":
                    if isinstance(cond_value, str):
                        try:
                            cond_value = [v.strip() for v in cond_value.split(",")]
                        except Exception:
                            return ToolFailure(
                                error=f"条件值 {cond_value} 解析失败，应为以逗号分隔的字符串列表（示例：value1,value2,value3）",
                                
                            )

                    else:
                        return ToolFailure(
                            error=f"条件值 {cond_value} 格式错误，应为以逗号分隔的字符串列表（示例：value1,value2,value3）",
                            
                        )
                    condition_mask = column_values.isin(cond_value)
                else:
                    return ToolFailure(
                        error=f"不支持的操作符: {operator}"
                    )

                if mask is None:
                    mask = condition_mask
                else:
                    mask = (
                        mask & condition_mask
                        if logic == "AND"
                        else mask | condition_mask
                    )

            if mask is not None:
                filtered_data = filtered_data[mask]

        if filtered_data.empty:
            return ToolFailure(
                error=f"所有过滤条件应用后，没有匹配的数据"
            )
        if columns is None:
            columns = filtered_data.columns.tolist()

        missing_columns = [
            column for column in columns if column not in filtered_data.columns
        ]
        if missing_columns:
            return ToolFailure(
                error=f"列 {column} 不存在于数据表 {table_name}"
            )

        if "csvTime" not in columns and "csvTime" in filtered_data.columns:
            columns.append("csvTime")

        for col in condition_columns:
            if col not in columns and col in filtered_data.columns:
                columns.append(col)

        result = {}
        for column in columns:
            if column == "csvTime":
                result[column] = (
                    filtered_data[column].dt.strftime("%Y-%m-%d %H:%M:%S").tolist()
                )
            else:
                result[column] = filtered_data[column].replace({pd.NA: None}).tolist()
        if not ignore_too_many and len(filtered_data) > max_length:
            return ToolFailure(
                error=f"查询数据过多或传参错误，请更改参数后重新调用函数",
                
            )
        if not ignore_too_many:
            logger.special("\n", render_text_table(result))

        return ToolResult(
            output={
                "result": result,
                "length": len(filtered_data),
                "column_desc": get_table_meta(self.table_meta_filepath, table_name, columns),
            },
            
        )
