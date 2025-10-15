# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import traceback
from typing import Dict, List

import pandas as pd
from tool.base import BaseTool, ToolFailure, ToolResult
from utils import get_table_meta
import logger


class DataAggregator(BaseTool):
    """数据聚合查询工具"""

    name: str = "data_aggregator"
    description: str = (
        "按指定列对数据进行聚合运算。输入：数据表名、起始时间、结束时间、列名、过滤条件、聚合方法（平均值、最大值、最小值、众数、求和、数据条数）。输出：指定时间范围内对指定列根据过滤条件进行聚合计算的结果。"
    )
    input: str = (
        "数据表名、起始时间、结束时间、列名、过滤条件、聚合方法（平均值、最大值、最小值、众数、求和、数据条数）。"
    )
    output: str = "指定时间范围内对指定列根据过滤条件进行聚合计算的结果。"
    examples: List[str] = ["2022/01/01 一号舵桨转舵A-Ua电压的平均值、和是多少？"]
    notices: List[str] = [
        "统计设备的运行时长、统计A架的摆动次数、查询平均值、最大值、最小值、求和或数据条数时，使用 data_aggregator 函数"
    ]
    parameters: dict = {
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "数据表名。"},
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
            "column": {"type": "string", "description": "需要进行聚合计算的列名。"},
            "method": {
                "type": "string",
                "enum": ["avg", "max", "min", "mode", "sum", "count"],
                "description": "聚合方法，支持 'avg'（平均值）、'max'（最大值）、'min'（最小值）、'mode'（众数）、'sum'（总和）、'count'（数据条数）。",
            },
            "conditions_logic": {
                "type": "string",
                "enum": ["AND", "OR"],
                "default": "AND",
                "description": "逻辑运算符，可选 'AND' 或 'OR'，用于组合多个条件。",
            },
            "conditions": {
                "type": "array",
                "description": "可选的过滤条件列表，每个条件包含列名、运算符和值。",
                "default": [],
                "items": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "过滤条件的列名。"},
                        "operator": {
                            "type": "string",
                            "enum": ["in", "==", ">", "<", ">=", "<=", "!="],
                            "description": "运算符，支持以下值：'in', '==', '>', '<', '>=', '<=', '!='。",
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
        "required": ["table_name", "start_time", "end_time", "column", "method"],
    }

    def execute(
        self,
        table_name: str,
        start_time: str,
        end_time: str,
        column: str,
        method: str,
        conditions_logic: str = "AND",
        conditions: List[Dict[str, str]] = None,
    ) -> ToolResult:
        """
        根据数据表名、开始时间、结束时间对指定列进行聚合操作，并支持按条件过滤。

        参数：
        table_name (str): 数据表名
        start_time (str): 开始时间，格式为 'YYYY-MM-DD HH:MM:SS'
        end_time (str): 结束时间，格式为 'YYYY-MM-DD HH:MM:SS'
        column (str): 需要进行聚合计算的列名
        method (str): 聚合方法，可选：
            - "avg"（平均值）
            - "max"（最大值）
            - "min"（最小值）
            - "mode"（众数）
            - "sum"（总和）
            - "count"（数据条数）
        conditions_logic (str): 过滤条件逻辑，支持AND、OR
        conditions (List[Dict[str, str]], 可选): 过滤条件，每个条件包含：
            - "column": 过滤列名
            - "operator": 过滤操作符（in, ==, >, <, >=, <=, !=）
            - "value": 过滤值

        返回：
        dict: 包含聚合结果的字典，或错误信息
        """
        try:
            df = pd.read_csv(f"{self.table_base_path}/{table_name}.csv")
        except FileNotFoundError:
            return ToolFailure(error=f"数据表 {table_name} 不存在")

        if "csvTime" not in df.columns:
            return ToolFailure(error="数据表缺少 csvTime 时间列")

        df["csvTime"] = pd.to_datetime(df["csvTime"], unit="ns")

        start_time = pd.to_datetime(start_time.replace("24:00:00", "23:59:59"))
        end_time = pd.to_datetime(end_time.replace("24:00:00", "23:59:59"))

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
                    error=f"未找到时间点 {start_time} 附近的数据"
                )

            filtered_data = closest_data
        else:
            filtered_data = df[
                (df["csvTime"] >= start_time) & (df["csvTime"] <= end_time)
            ]

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

        if column not in filtered_data.columns:
            return ToolFailure(
                error=f"列 {column} 不存在于数据表 {table_name}"
            )

        values = filtered_data[column].dropna()

        try:
            if method == "avg":
                result = values.mean()
            elif method == "max":
                result = values.max()
            elif method == "min":
                result = values.min()
            elif method == "mode":
                result = values.mode()[0] if not values.mode().empty else None
            elif method == "sum":
                result = values.sum()
            elif method == "count":
                result = len(values)
            else:
                return ToolFailure(error=f"不支持的聚合方法: {method}")
        except Exception as e:
            logger.error("聚合失败", e)
            logger.error(traceback.format_exc())
            return ToolFailure(error=f"聚合错误: {e}")

        return ToolResult(
            output={
                f"{column}_{method}": (
                    round(result, 2) if isinstance(result, float) else result
                ),
                "column_desc": get_table_meta(
                    self.table_meta_filepath, table_name, [column]
                ),
            },
            
        )
