# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import traceback
from typing import List
from tool.base import BaseTool, ToolFailure, ToolResult
import logger


class MathCalculator(BaseTool):
    """数学运算工具"""

    name: str = "math_calculator"
    description: str = (
        "进行数学运算。输入：运算类型（加法、减法、乘法、除法、求和、求平均值、求最大值、求最小值、求绝对值、求列表长度）、操作数列表。输出：运算结果。求列表长度时，操作数列表支持数字、字符串、日期等。"
    )
    input: str = (
        "运算类型（加法、减法、乘法、除法、求和、求平均值、求最大值、求最小值、求绝对值、求列表长度）、操作数列表。求列表长度时，操作数列表支持数字、字符串、日期等"
    )
    output: str = "运算结果"
    notices: List[str] = [
        "统计天数时必须调用math_calculator函数，不得手动计数",
    ]
    parameters: dict = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "指定运算类型，支持以下值： '加法'、'减法'、'乘法'、'除法'、'求和'、'求平均值'、'求最大值'、'求最小值'、'求绝对值'、'求列表长度'。",
                "enum": [
                    "加法",
                    "减法",
                    "乘法",
                    "除法",
                    "求和",
                    "求平均值",
                    "求最大值",
                    "求最小值",
                    "求绝对值",
                    "求列表长度",
                ],
            },
            "operands": {
                "type": "array",
                "description": "参与运算的数值列表，所有元素必须为数字（求列表长度时，操作数列表支持数字、字符串、日期等）。乘法、减法、除法的操作数至少为2个",
                "items": {"type": "number"},
            },
        },
        "required": ["operation", "operands"],
    }

    def execute(self, operation, operands) -> ToolResult:
        """
        进行数学运算，包括加法、减法、乘法、除法、求和、求绝对值和求平均值。

        :param operation (str): 运算类型，支持 '加法'、'减法'、'乘法'、'除法'、'求和'、'求平均值'、'求绝对值'、'求最大值'、'求最小值'、'求列表长度'。
        :param operands (list): 数值列表，所有元素必须为数字（求列表长度时，操作数列表支持数字、字符串、日期等）。

        :return ToolResult: 运算结果
        """
        try:
            if not operands:
                return ToolFailure(error="操作数不能为空")

            if operation == "加法":
                result = sum(operands)
            elif operation == "减法":
                result = operands[0]
                for num in operands[1:]:
                    result -= num
            elif operation == "乘法":
                if len(operands) == 1:
                    return ToolFailure(
                        error="乘法错误：操作数至少为2个"
                    )

                result = 1
                for num in operands:
                    result *= num
            elif operation == "除法":
                if len(operands) == 1:
                    return ToolFailure(
                        error="除法错误：操作数至少为2个"
                    )
                result = operands[0]
                for num in operands[1:]:
                    if num == 0:
                        return ToolFailure(
                            error="除法错误：除数不能为0"
                        )
                    result /= num
            elif operation == "求和":
                result = sum(operands)
            elif operation == "求平均值":
                result = sum(operands) / len(operands)
            elif operation == "求最大值":
                result = max(operands)
            elif operation == "求最小值":
                result = min(operands)
            elif operation == "求列表长度":
                result = len(operands)
            elif operation == "求绝对值":
                result = [abs(num) for num in operands]
            else:
                return ToolFailure(
                    error="不支持的运算类型: {}".format(operation)
                )
            return ToolResult(
                output={
                    "result": result,
                },
                
            )

        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            return ToolFailure(error="运算错误: {}".format(str(e)))
