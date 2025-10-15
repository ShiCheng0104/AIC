# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import traceback
from typing import Dict, List

import pandas as pd
from llm import LLM
from tool.base import BaseTool, ToolFailure, ToolResult
from utils import get_table_meta
import logger


class PythonCodeGenerator(BaseTool):
    """Python代码生成工具"""

    name: str = "generate_simple_python_code"
    description: str = (
        "当现有工具无法满足需求且任务可通过简洁的 Python 代码准确实现时，调用此函数，利用大模型根据任务要求生成 Python 代码。"
    )
    input: str = "需要使用Python代码实现的任务描述"
    output: str = "Python代码"
    parameters: dict = {
        "type": "object",
        "properties": {
            "task_description": {
                "type": "string",
                "description": "详细描述任务，包括输入、预期输出及注意事项。",
            }
        },
        "required": ["task_description"],
    }

    def execute(self, task_description: str) -> ToolResult:
        """
        调用大模型生成简单的 Python 代码。

        :param task_description (str): 任务描述，包括输入、输出和注意事项。
        :return ToolResult: 生成的 Python 代码
        """

        from utils import parse_code

        CODE_GENERATE_PROMPT = f"""
        # 任务描述  
        {task_description}

        # 代码要求
        1. 生成的代码应该能够实现任务描述中的功能。
        2. 返回结果存在变量 `result` 中。

        # 输出要求  
        适当的思考过程是有益的，但最终必须输出代码。确保输出格式如下，并且只包含一个代码块：

        ```python  
        你的代码
        ```
        """
        messages = [
            {
                "role": "system",
                "content": "你是一个精通 Python 的编程助手，能够生成简洁且高效准确的 Python 代码。",
            },
            {"role": "user", "content": CODE_GENERATE_PROMPT},
        ]

        response = LLM().ask(messages)

        try:
            python_code = parse_code(response)
            return ToolResult(output=python_code)
        except Exception as e:
            return ToolFailure(error=f"生成代码失败: {e}")
