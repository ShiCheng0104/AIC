# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import traceback
import logger
from agent.base import BaseAgent
from knowledge import Knowledge
from prompt.critic import CORRECT_PROMPT
from prompt.vote import VOTE_PROMPT
from schema import ProblemSolution, ReasoningAnswer, VoteResult
from utils import parse_res


class CriticAgent(BaseAgent):
    """负责执行纠错、投票任务的 Agent"""

    name: str = "CriticAgent"
    description: str = "负责执行纠错、投票任务的 Agent"

    def act(self, *args, **kwargs):
        return super().act(*args, **kwargs)

    def vote(
        self, id: str, question: str, vote_times: int, solutions: list[ProblemSolution]
    ) -> VoteResult:
        """
        多次调用 get_answer 获取答案，并让 LLM 评估选出最优答案

        :param id: 问题 ID
        :param question: 问题
        :param vote_times: 采样次数
        :return: LLM 评估后选出的最佳答案
        """

        vote_res = VoteResult(id, question, vote_times)
        vote_res.solutions = solutions

        if len(vote_res.solutions) == 1:
            vote_res.final_answer = vote_res.solutions[0].reasoning_answer
            return vote_res
        elif len(vote_res.solutions) == 0:
            vote_res.final_answer = ReasoningAnswer(answer="")
            return vote_res

        try:
            answer_content = "\n".join(
                [
                    f"答案 {i+1}: {result}"
                    for i, result in enumerate(vote_res.get_answers())
                ]
            )
            messages = [
                {"role": "system", "content": self.get_prompt_vote()},
                {"role": "user", "content": f"问题：{question}\n{answer_content}"},
            ]
            logger.info(f"【开始投票】问题：{question}\n{answer_content}")

            best_answer = parse_res(self.llm.ask(messages))
            vote_res.final_answer = ReasoningAnswer(best_answer)
        except Exception:
            logger.error(f"【第{id}题投票错误】\n{traceback.format_exc()}")
            vote_res.final_answer = vote_res.solutions[0].reasoning_answer

        return vote_res

    def get_prompt_vote(self) -> str:
        """
        获得投票模板

        :return: 投票模板
        """
        return VOTE_PROMPT

    def correct(self, solution: ProblemSolution, times: int = 3) -> ReasoningAnswer:
        """
        获得问题纠错的答案

        :param solution: 问题解答
        :return: 问题纠错的答案
        """
        logger.info(f"【开始纠错问题{solution.id}的答案】", solution.to_correct_json())
        messages = [
            {
                "role": "system",
                "content": self.get_prompt_correct(solution.question),
            },
            {
                "role": "user",
                "content": str(solution.to_correct_json()),
            },
        ]
        response = self.llm.ask(messages)
        try:
            res_answer = solution.reasoning_answer.clone()
            res = json.loads(parse_res(response))
            res_answer.corrected_reasoning = res["corrected_reasoning"]
            res_answer.corrected_answer = res["corrected_answer"]
            res_answer.correct = res["correct"]
            return res_answer
        except Exception as e:
            logger.error(f"【问题{solution.id}纠错出错】\n{traceback.format_exc()}")
            if times > 0:
                return self.get_correct(times - 1)

    def get_prompt_correct(self, question: str) -> str:
        """
        获得问题纠错模板

        :return: 问题纠错模板
        """
        res = CORRECT_PROMPT
        res = res.replace("<<knowledge>>", self.get_knowledge(question=question))
        return res

    def get_knowledge(self, question: str) -> str:
        return str(Knowledge.retrieve_knowledge(question, False))
