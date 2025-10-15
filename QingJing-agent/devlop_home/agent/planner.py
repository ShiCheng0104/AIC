# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json

import concurrent
import traceback
import utils
from agent.actor import ActorAgent
from agent.base import BaseAgent
from knowledge import Knowledge
from prompt.planner import PLANNER_PROMPT, UPDATE_PLAN_PROMPT
from prompt.preflight import PREFLIGHT_TOOL_PROMPT
from prompt.summary import SUMMARY_ONLY_ANSWER_PROMPT, SUMMARY_PROMPT
from schema import Decomposition, ProblemSolution, ReasoningAnswer, Subtask
from tool.tool_pool import ToolPool
from utils import parse_res
import logger

prompt_task_decomposition_file = "devlop_home/prompts/task_decomposition.md"


class PlannerAgent(BaseAgent):
    """负责进行任务分解、更新任务树、总结的Agent"""

    name: str = "PlannerAgent"
    description: str = "负责进行任务分解、更新任务树、总结的Agent"
    id: str
    question: str

    def act(self) -> ProblemSolution:
        solution = ProblemSolution(self.id, self.question)

        decomposition = self.get_planning()
        if not decomposition.raw_question:
            decomposition.raw_question = solution.question
        solution.decomposition = decomposition
        solution.init_decomposition = decomposition.clone()

        tasks_by_level, sorted_levels = PlannerAgent.group_tasks_by_level(
            decomposition.subtasks
        )
        current_index = 0

        while current_index < len(sorted_levels):
            current_level = sorted_levels[current_index]
            level_tasks: list[Subtask] = tasks_by_level[current_level]

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=utils.module_config.max_workers_subtask
            ) as executor:
                futures = []
                for task in level_tasks:
                    if not task.completed():
                        futures.append(
                            executor.submit(self.handle_task, task, decomposition)
                        )

                for future in concurrent.futures.as_completed(futures):
                    future.result()

            if (
                utils.module_config.enable_update_decomposition
                and current_level != sorted_levels[-1]
            ):
                decomposition = self.update_planning(self.question, decomposition)
                solution.decomposition = decomposition
                tasks_by_level, sorted_levels = PlannerAgent.group_tasks_by_level(
                    decomposition.subtasks
                )
                if current_level == sorted_levels[-1]:
                    break

            current_index += 1

        solution.reasoning_answer = ReasoningAnswer(
            solution.decomposition.subtasks[-1].answer
        )
        if utils.module_config.enable_summary:
            reasoning_answer = self.summary(solution)
            if reasoning_answer:
                solution.reasoning_answer = reasoning_answer
        return solution

    @staticmethod
    def group_tasks_by_level(subtasks):
        """
        将子任务按级别分组，并返回按级别排序的任务字典。

        :param subtasks: 子任务列表，包含多个任务对象，每个任务对象需要有 `level` 属性。
        :return: 一个字典，按任务级别分组，并且级别已排序。
        """
        tasks_by_level = {}

        for task in subtasks:
            if task.level not in tasks_by_level:
                tasks_by_level[task.level] = []
            tasks_by_level[task.level].append(task)

        sorted_levels = sorted(tasks_by_level.keys())
        return tasks_by_level, sorted_levels

    def summary(self, solution: ProblemSolution, times: int = 3) -> ReasoningAnswer:
        """
        获得问题总结的答案

        :param solution: 问题解答
        :return: 问题总结的答案
        """
        logger.info(f"【开始总结问题{solution.id}的答案】", solution.to_summary_str())
        messages = [
            {
                "role": "system",
                "content": self.get_prompt_summary(),
            },
            {
                "role": "user",
                "content": solution.to_summary_str(),
            },
        ]
        response = self.llm.ask(
            messages, tools=ToolPool.get_calculate_tools().to_param()
        )
        try:
            res = json.loads(parse_res(response))
            res_answer = ReasoningAnswer.from_dict(res)
            logger.special(f"【问题{solution.id}的总结结果】: \n{res_answer}")
            return res_answer
        except Exception as e:
            logger.error(f"【问题{solution.id}总结出错】\n{traceback.format_exc()}")
            if times > 0:
                return self.summary(solution, times - 1)
            else:
                return None

    def get_prompt_summary(self) -> str:
        """
        获得问题总结模板

        :param question: 问题
        :return: 问题总结模板
        """
        res = SUMMARY_PROMPT
        if utils.module_config.summary_only_answer:
            res = SUMMARY_ONLY_ANSWER_PROMPT
        return res

    def get_planning(self) -> Decomposition:
        """
        获得问题的分解结果

        :return: 问题的分解结果
        """
        logger.info(f"【开始获取问题{self.id}的分解结果】", self.question)
        tools = self.get_tool()
        messages = [
            {
                "role": "system",
                "content": self.get_planning_prompt(tools=tools),
            },
            {
                "role": "user",
                "content": self.question,
            },
        ]
        response = self.llm.ask(messages)
        res = json.loads(parse_res(response))
        decomposition = Decomposition.from_dict(res)
        decomposition.need_tools = tools
        decomposition.draw_table()
        return decomposition

    def update_planning(self, decomposition: Decomposition) -> Decomposition:
        """
        询问 LLM 是否需要更新任务分解树

        :param decomposition: 问题的分解结果
        :return: 更新后的decomposition
        """
        logger.debug("【开始更新任务分解树】")
        user_prompt = "已知初始任务问题为：<<question>> \n 当前任务分解树如下:<<decomposition>>\n 是否需要更新任务分解树？"
        messages = [
            {
                "role": "system",
                "content": self.get_prompt_update_decomposition(),
            },
            {
                "role": "user",
                "content": user_prompt.replace(
                    "<<question>>", str(self.question)
                ).replace("<<decomposition>>", str(decomposition.to_update_dict())),
            },
        ]
        response = self.llm.ask(messages)

        try:
            res = json.loads(parse_res(response))
        except Exception as e:
            try:
                logger.error(f"【更新任务分解树出错】\n{traceback.format_exc()}")
                logger.info("【尝试修改任务分解树Json格式】")
                res = json.loads(parse_res(response).replace("None", "null"))
                logger.info("【修改成功】\n")
            except Exception as e:
                logger.error("【修改失败，直接返回原任务分解树】\n")
                logger.error(f"{parse_res(response)}")
                return decomposition

        res_decomposition = Decomposition.from_dict(res)
        for subtask in res_decomposition.subtasks:
            init_task = decomposition.get_task_by_id(subtask.task_id)
            if init_task and init_task.completed():
                subtask.answer = init_task.answer
                subtask.need_tools = init_task.need_tools
                subtask.need_tables = init_task.need_tables
                subtask.function_results = init_task.function_results
                subtask.parent_tasks = init_task.parent_tasks
        res_decomposition.need_tools = decomposition.need_tools
        res_decomposition.raw_question = decomposition.raw_question
        res_decomposition.draw_table()
        return res_decomposition

    def get_prompt_update_decomposition(self) -> str:
        """
        获得任务分解更新模板

        :param question: 问题
        :return: 任务分解模板
        """
        res = UPDATE_PLAN_PROMPT
        res = res.replace("<<knowledge>>", self.get_knowledge())
        return res

    def handle_task(self, task: Subtask, decomposition: Decomposition):
        """
        在单独的线程中处理每个子任务

        :param task: 子任务
        :param decomposition: 分解结果
        """
        parent_tasks = []
        for parent_id in task.parent_ids:
            parent_task = decomposition.get_task_by_id(parent_id)
            if parent_task:
                parent_tasks.append(parent_task)

        actor = ActorAgent(
            task=task,
            assumption=decomposition.assumption,
            raw_question=decomposition.raw_question,
            chain_of_subtasks=decomposition.chain_of_subtasks,
            contains_time=decomposition.contains_time,
            parent_tasks=parent_tasks,
        )
        actor.act()

    def get_tool(self) -> list:
        """
        获得问题所需的工具

        :return: 所需工具的名称列表
        """
        logger.debug(f"【开始获取初始问题{self.id}所需工具】", self.question)
        messages = [
            {
                "role": "system",
                "content": self.get_prompt_get_tool(),
            },
            {
                "role": "user",
                "content": self.question,
            },
        ]
        response = self.llm.ask(messages)
        tools = json.loads(parse_res(response))
        if "math_calculator" not in tools:
            tools.append("math_calculator")
        logger.info("【问题所需工具】", tools)
        return tools

    def get_prompt_get_tool(self) -> str:
        """
        生成可能所需的工具的 Prompt

        :param question: 问题
        :return: Prompt
        """
        res = PREFLIGHT_TOOL_PROMPT
        res = res.replace("<<knowledge>>", self.get_knowledge())
        res = res.replace("<<tools>>", ToolPool.get_all_tools().to_desc())
        return res

    def get_planning_prompt(self, tools: list[str]) -> str:
        """
        获得任务分解System指令

        :return: 任务分解System指令
        """
        res = PLANNER_PROMPT
        res = res.replace(
            "<<function_calls>>", ToolPool.get_tools_by_names(tools).to_desc()
        )
        res = res.replace("<<knowledge>>", self.get_knowledge())
        return res

    def get_knowledge(self):
        return str(Knowledge.retrieve_knowledge(self.question, False))
