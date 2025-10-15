# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import traceback
from typing import List
import logger, prompt, utils
from agent.base import BaseAgent
from knowledge import Knowledge
from prompt.actor import ACTOR_PROMPT, REWRITE_PROMPT
from prompt.preflight import PREFLIGHT_TABLE_AND_TOOL_PROMPT
from schema import Decomposition, Subtask
from tool.tool_collection import ToolCollection
from tool.tool_pool import ToolPool


class ActorAgent(BaseAgent):
    """负责解决原子问题的 Agent（重写原子问题、获取数据表结构、执行工具函数）"""

    name: str = "ActorAgent"
    description: str = (
        "负责解决原子问题的 Agent（重写原子问题、获取数据表结构、执行工具函数）"
    )

    task: Subtask
    assumption: str
    raw_question: str
    chain_of_subtasks: str
    contains_time: bool
    parent_tasks: List[Subtask]

    def question(self) -> str:
        return self.task.question

    def act(self) -> Subtask:
        """
        获得原子问题的答案

        :param decomposition: 问题的分解结果
        :param task: 原子问题
        :param parent_tasks: 父任务
        """
        logger.info("【开始获取原子问题答案】", self.question())

        self.rewrite_atomic_question()

        table_meta_list, tool_collection = self.get_table_meta_and_tool()

        system_prompt, user_prompt = self.get_prompt_atomic_question(table_meta_list)
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]
        response = self.llm.ask(messages, tool_collection.to_param())
        messages.append(response.choices[0].message.model_dump())

        function_results = []
        for _ in range(utils.module_config.max_function_calling_iterations):
            if not response.choices[0].message.tool_calls:
                break
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                if function_name in ToolPool.get_all_tools().names():
                    try:
                        logger.debug(f"【开始执行工具函数{function_name}】", args)
                        function_result = ToolPool.execute(
                            name=function_name, args=args
                        ).to_dict()
                        function_results.append(function_result)
                        logger.info(
                            f"【工具函数{function_name}执行结果】", function_result
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "content": str(function_result),
                                "tool_call_id": tool_call.id,
                            }
                        )
                    except Exception:
                        logger.warning(
                            f"【工具函数{function_name}执行失败】",
                            args,
                            "\n",
                            traceback.format_exc(),
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "content": f"工具函数执行失败，请检查函数参数是否错误：{args}",
                                "tool_call_id": tool_call.id,
                            }
                        )
                else:
                    logger.warning(f"【未找到工具函数{function_name}】")
                    messages.append(
                        {
                            "role": "tool",
                            "content": f"未找到工具函数{function_name}",
                            "tool_call_id": tool_call.id,
                        }
                    )

            response = self.llm.ask(messages, tool_collection.to_param())
            messages.append(response.choices[0].message.model_dump())

        answer = utils.parse_res(response)
        logger.success("【原子问题答案】", answer)
        self.task.answer = answer
        self.task.function_results = function_results
        self.task.need_tools = tool_collection.names()
        self.task.need_tables = [table["table_name"] for table in table_meta_list]
        return self.task

    def get_prompt_atomic_question(
        self, table_meta_list: list[dict]
    ) -> tuple[str, str]:
        """
        获得原子问题模板

        :param task: 原子问题
        :param assumption: 假设条件
        :param table_meta_list: 数据表结构列表
        """
        system_prompt = ACTOR_PROMPT
        system_prompt = (
            system_prompt.replace("<<knowledge>>", self.get_knowledge())
            .replace("<<table_meta_list>>", str(table_meta_list))
            .replace("<<chain_of_subtasks>>", str(self.chain_of_subtasks))
        )

        if self.assumption:
            system_prompt = system_prompt.replace("<<assumption>>", self.assumption)

        user_prompt = """
        已知上游任务执行结果：<<parent_tasks_desc>>
        当前要求解的子任务为：<<<question>>>
        """

        user_prompt = user_prompt.replace(
            "<<question>>", f"【子任务{self.task.task_id}】{self.question()}"
        ).replace("<<parent_tasks_desc>>", str(self.get_parent_tasks_desc()))

        return system_prompt, user_prompt

    def rewrite_atomic_question(self):
        """
        重写原子问题

        :param decomposition: 问题的分解结果
        :param task: 原子问题
        """
        if (
            utils.module_config.enable_rewrite_atomic_question
            and self.has_parent_task()
        ):
            logger.debug("【开始重写原子问题】", self.question())
            system_prompt, user_prompt = self.get_prompt_rewrite_atomic_question()
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]
            response = self.llm.ask(messages)
            try:
                rewritten_question = str(utils.parse_res(response))
                logger.special(
                    "【重写原子问题】",
                    f"原问题：{self.question()}----->重写后的问题：{rewritten_question}",
                )
                self.task.question = rewritten_question
            except Exception as e:
                logger.error(f"【原子问题预处理出错】\n{traceback.format_exc()}")

    def get_prompt_rewrite_atomic_question(self) -> tuple[str, str]:
        """
        获得重写原子问题模板

        :param task: 原子问题
        :param assumption: 假设条件
        """
        system_prompt = REWRITE_PROMPT
        system_prompt = system_prompt.replace("<<knowledge>>", self.get_knowledge())

        if self.assumption:
            system_prompt = system_prompt.replace("<<assumption>>", self.assumption)

        user_prompt = """
        当前要求解的子任务为：<<question>>
        
        已知初始问题：<<raw_question>>

        已知任务分解链：<<chain_of_subtasks>>

        已知其上游任务执行结果：<<parent_tasks_desc>>
        """
        parent_tasks_desc = ""
        for task_desc in self.get_parent_tasks_desc():
            if task_desc["answer"]:
                parent_tasks_desc += task_desc["answer"] + "\n"

        user_prompt = (
            user_prompt.replace(
                "<<question>>", f"【子任务{self.task.task_id}】{self.question()}"
            )
            .replace("<<parent_tasks_desc>>", parent_tasks_desc)
            .replace("<<raw_question>>", str(self.raw_question))
            .replace("<<chain_of_subtasks>>", str(self.chain_of_subtasks))
        )

        return system_prompt, user_prompt

    def get_table_meta_and_tool(self) -> tuple[list[dict], ToolCollection]:
        """
        获得问题所需的数据表的元信息和所需工具

        :param decomposition: 问题的分解结果
        :param task: 原子问题
        :return: 数据表的元信息和所需工具
        """
        logger.debug("【开始获取原子问题所需数据表和工具】", self.question())
        messages = [
            {
                "role": "user",
                "content": self.get_prompt_get_table_meta_and_tool(),
            },
        ]
        response = self.llm.ask(messages)
        res = json.loads(utils.parse_res(response))
        tables = res.get("tables", [])
        tools = res.get("tools", [])

        if (
            self.question().find("比例") != -1
            and "before_or_late_ratio_calculator" not in tools
        ):
            tools.append("before_or_late_ratio_calculator")
        if not self.contains_time and "设备参数详情" not in tables:
            tables.append("设备参数详情")
        if len(tools) == 1 and tools[0] in [
            "energy_usage_calculator",
            "power_fuel_calculator",
        ]:
            tables = []
        if "math_calculator" not in tools:
            tools.append("math_calculator")

        logger.info("【原子问题所需数据表】", tables, "【所需工具】", tools)
        return Knowledge.get_table_desc_by_names(tables), ToolPool.get_tools_by_names(
            tools
        )

    def get_prompt_get_table_meta_and_tool(self) -> str:
        """
        生成数据表结构查询的 Prompt

        :param task: 问题
        :param assumption: 假设条件
        :return: Prompt
        """
        res = PREFLIGHT_TABLE_AND_TOOL_PROMPT
        res = res.replace("<<knowledge>>", self.get_knowledge())
        res = res.replace("<<tools>>", ToolPool.get_all_tools().to_desc())
        res = res.replace("<<table_desc>>", Knowledge.get_tables_desc())
        if self.assumption:
            res = res.replace("<<assumption>>", self.assumption)
        res = res.replace(
            "<<question>>", f"【子任务{self.task.task_id}】{self.question()}"
        )
        res = res.replace("<<parent_tasks_desc>>", str(self.get_parent_tasks_desc()))
        return res

    def get_knowledge(self):
        return str(Knowledge.retrieve_knowledge(self.question(), False))

    def get_parent_tasks_desc(self) -> list[dict]:
        if not self.has_parent_task():
            return ""
        return [task.to_simple_dict() for task in self.parent_tasks]

    def has_parent_task(self) -> bool:
        return self.parent_tasks and len(self.parent_tasks) > 0
