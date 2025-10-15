# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import traceback
import logger, utils
from agent.critic import CriticAgent
from agent.planner import PlannerAgent
from schema import ProblemSolution, VoteResult

replace_filepath = "devlop_home/knowledge/replace.json"

replace_dict = {
    "运行时间定义为发电机在额定转速下的运行时间，额定转速运行值为1表示发电机运行了1分钟。": "",
    "平均作业时长": "平均每天作业时长",
    "总运行时间": "总运行时长",
    "回收过程": "回收阶段",
    "布放过程": "布放阶段",
    "进行该动作时": "此时",
    "从征服者出水（约-43°）到落座（约35°）A架右舷摆过的角度可以记为一次完整的摆动（反之亦然），": "",
    "假设A架右舷同一方向上摆动超过10°即可算作一次摆动，": "同方向摆动，",
    "发电机的运行时间": "发电机的运行时长",
    "请根据提供的1~4号柴油发电机的燃油消耗量，": "",
}


def get_solution(index: int, id: str, question: str) -> ProblemSolution:
    """
    获得问题的答案，返回最终答案

    :param id: 问题 ID
    :param question: 问题
    :return: 问题解答
    """
    try:
        logger.info(f"【开始第{index}次获取问题{id}答案】")
        solution = PlannerAgent(id=id, question=question).act()
        if utils.module_config.enable_correct:
            reasoning_answer = CriticAgent().correct(solution)
            if reasoning_answer:
                solution.reasoning_answer = reasoning_answer
        logger.success(
            f"【第{index}次得到的{id}最终答案】",
            str(solution.reasoning_answer),
        )
        return solution
    except Exception:
        logger.error(f"【第{index}次获取问题{id}的答案出错】\n{traceback.format_exc()}")


def handle_question(query):
    """
    预处理问题
    """
    for key, value in replace_dict.items():
        query = query.replace(key, value)
    return query


def process_one(line: dict,socketio) -> VoteResult | dict:
    """
    获取一个问题的解决过程及答案
    """
    id = line["id"]
    question = handle_question(line["question"])

    try:
        logger.info(f"【开始获取问题{id}的答案】", question)
        solutions = []
        for i in range(utils.module_config.vote_times):
            solution = utils.try_run(get_solution, i + 1, id, question)
            if solution:
                solutions.append(solution)
        vote_res = CriticAgent().vote(
            id, question, utils.module_config.vote_times, solutions
        )
        vote_res.init_question = line["question"]
        logger.special(
            f"【{id}的最终答案】:\n",
            vote_res.final_answer.get_correct_answer(),
        )
        return vote_res
    except Exception as e:
        logger.error(f"【获取问题{id}的答案出错】\n{traceback.format_exc()}")
        return {"id": id, "question": line["question"], "answer": str(e)}
