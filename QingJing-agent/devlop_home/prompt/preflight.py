# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

PREFLIGHT_TOOL_PROMPT = """已知可调用的函数工具：<<tools>>
已知背景知识：<<knowledge>>

请基于工具和已知条件，回答用户输入的问题所需的工具，要求：

- 分析解决该问题可能需要的工具；
- 涉及计算的问题尽可能选择对应的工具；
- 请先仔细思考，但仅需返回最终结果，不需要提供思考过程；
- 输出格式：仅返回 JSON 格式的工具列表，例如：
  ["tool1", "tool2"]
  
以下是用户输入的问题：
"""

PREFLIGHT_TABLE_AND_TOOL_PROMPT = """当前需要执行的子任务：<<question>>
已知背景知识：<<knowledge>>
假设条件：<<assumption>>

已知上游任务执行结果：<<parent_tasks_desc>>

请基于数据表、工具和假设条件回答当前子任务所需的数据表和工具：

已知可用的数据表：<<table_desc>>
已知可调用的函数工具：<<tools>>

要求：
- 分析问题的背景知识和已知条件与数据表的描述进行对比，判断必需的数据表，准确给出表名；
- 分析问题的背景知识和已知条件与工具的描述进行对比，判断该工具是否适用，准确给出工具名；
- 涉及计算的问题尽可能选择对应的工具
- 若已知条件或工具可独立解决问题，无需使用数据表；
- 请先仔细思考，但仅需返回最终结果，不需要提供思考过程；
- 输出格式：仅返回 JSON 格式的所需数据表名列表和工具列表，例如：
  {
      "tables": ["table1", "table2"],
      "tools": ["tool1", "tool2"]
  }
"""
