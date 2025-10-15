# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

"""
定义投票、问题、子问题、分解、API响应等类
"""

import copy
from enum import Enum

from pydantic import BaseModel, Field

import logger

from typing import Any, List, Literal, Optional, Union


class Role(str, Enum):
    """Message role options"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


ROLE_VALUES = tuple(role.value for role in Role)
ROLE_TYPE = Literal[ROLE_VALUES]


class ToolChoice(str, Enum):
    """Tool choice options"""

    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"


TOOL_CHOICE_VALUES = tuple(choice.value for choice in ToolChoice)
TOOL_CHOICE_TYPE = Literal[TOOL_CHOICE_VALUES]


class Function(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    """Represents a tool/function call in a message"""

    id: str
    type: str = "function"
    function: Function


class Message(BaseModel):
    """Represents a chat message in the conversation"""

    role: ROLE_TYPE = Field(...)  # type: ignore
    content: Optional[str] = Field(default=None)
    tool_calls: Optional[List[ToolCall]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)

    def __add__(self, other) -> List["Message"]:
        """支持 Message + list 或 Message + Message 的操作"""
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """支持 list + Message 的操作"""
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """Convert message to dictionary format"""
        message = {"role": self.role}
        if self.content is not None:
            message["content"] = self.content
        if self.tool_calls is not None:
            message["tool_calls"] = [
                tool_call.model_dump() for tool_call in self.tool_calls
            ]
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        return message

    @classmethod
    def user_message(cls, content: str) -> "Message":
        """Create a user message"""
        return cls(role=Role.USER, content=content)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        """Create a system message"""
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def assistant_message(cls, content: Optional[str] = None) -> "Message":
        """Create an assistant message"""
        return cls(role=Role.ASSISTANT, content=content)

    @classmethod
    def tool_message(cls, content: str, name, tool_call_id: str) -> "Message":
        """Create a tool message"""
        return cls(
            role=Role.TOOL,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
        )

    @classmethod
    def from_tool_calls(
        cls,
        tool_calls: List[Any],
        content: Union[str, List[str]] = "",
        **kwargs,
    ):
        """Create ToolCallsMessage from raw tool calls.

        Args:
            tool_calls: Raw tool calls from LLM
            content: Optional message content
            base64_image: Optional base64 encoded image
        """
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=formatted_calls,
            **kwargs,
        )


class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        """Add a message to memory"""
        self.messages.append(message)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def add_messages(self, messages: List[Message]) -> None:
        """Add multiple messages to memory"""
        self.messages.extend(messages)

    def clear(self) -> None:
        """Clear all messages"""
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get n most recent messages"""
        return self.messages[-n:]

    def to_dict_list(self) -> List[dict]:
        """Convert messages to list of dicts"""
        return [msg.to_dict() for msg in self.messages]


class ModuleConfig:
    def __init__(
        self,
        enable_update_decomposition=True,
        enable_summary=True,
        enable_correct=False,
        enable_rewrite_atomic_question=True,
        vote_times=1,
        max_workers_main=20,
        max_workers_subtask=5,
        max_function_calling_iterations=6,
        summary_only_answer=True,
    ):
        self.enable_update_decomposition = enable_update_decomposition
        self.enable_summary = enable_summary
        self.enable_correct = enable_correct
        self.enable_rewrite_atomic_question = enable_rewrite_atomic_question
        self.vote_times = vote_times
        self.max_workers_main = max_workers_main
        self.max_workers_subtask = max_workers_subtask
        self.max_function_calling_iterations = max_function_calling_iterations
        self.summary_only_answer = summary_only_answer

    def to_dict(self):
        """将配置转换为字典"""
        return {
            "enable_update_decomposition": self.enable_update_decomposition,
            "enable_summary": self.enable_summary,
            "enable_correct": self.enable_correct,
            "enable_rewrite_atomic_question": self.enable_rewrite_atomic_question,
            "vote_times": self.vote_times,
            "max_workers_main": self.max_workers_main,
            "max_workers_subtask": self.max_workers_subtask,
            "max_function_calling_iterations": self.max_function_calling_iterations,
            "summary_only_answer": self.summary_only_answer,
        }

    @classmethod
    def from_dict(cls, config_dict):
        """从字典创建配置对象"""
        return cls(**config_dict)

    def __repr__(self):
        return f"ModuleConfig({self.to_dict()})"


class ApiConfig:
    """API 配置对象"""

    def __init__(
        self,
        config_name: str,
        type: str,
        model: str,
        base_url: Optional[str] = None,
        api_key_env: Optional[str] = None,
        temperature: Optional[float] = 0,
        stream: Optional[bool] = False,
    ):
        self.config_name = config_name
        self.type = type
        self.model = model
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.temperature = temperature
        self.stream = stream

    def __repr__(self):
        return (
            f"ApiConfig(config_name='{self.config_name}', type='{self.type}', "
            f"model='{self.model}', base_url='{self.base_url}', api_key_env='{self.api_key_env}')"
        )

    @classmethod
    def from_dict(cls, data):
        return cls(
            config_name=data["config_name"],
            type=data["type"],
            model=data["model"],
            base_url=data.get("base_url"),
            api_key_env=data.get("api_key_env"),
            temperature=data.get("temperature", 0),
            stream=data.get("stream", False),
        )


class ReasoningAnswer:
    """
    带有推理过程的答案
    """

    def __init__(self, answer: str = None):
        self.reasoning: str = None
        self.answer: str = answer
        self.corrected_reasoning: str = None
        self.corrected_answer: str = None
        self.correct: str = None

    def get_correct_answer(self) -> str:
        return self.corrected_answer if self.corrected_answer else self.answer

    def get_correct_reasoning(self) -> str:
        return self.corrected_reasoning if self.corrected_reasoning else self.reasoning

    def __repr__(self):
        result = "思维过程：\n"
        reasoning = self.get_correct_reasoning()
        if reasoning is not None:
            result += reasoning + "\n"
        if self.correct is not None:
            result += f"纠错步骤：\n{self.correct}\n"
        answer = self.get_correct_answer()
        if answer is not None:
            result += f"最终答案：\n{answer}"

        return result

    def to_dict(self):
        return {
            "reasoning": self.reasoning,
            "answer": self.answer,
            "correct": self.correct,
            "corrected_reasoning": self.corrected_reasoning,
            "corrected_answer": self.corrected_answer,
        }

    def __json__(self):
        return self.to_dict()

    @classmethod
    def from_dict(cls, data):
        instance = cls()
        instance.reasoning = data.get("reasoning", None)
        instance.correct = data.get("correct", None)
        instance.answer = data.get("answer", None)
        instance.corrected_answer = data.get("corrected_answer", None)
        instance.corrected_reasoning = data.get("corrected_reasoning", None)
        return instance

    def clone(self):
        return copy.deepcopy(self)


class FunctionResult:
    """
    函数调用结果
    """

    def __init__(self, function_name, args):
        self.function_name = function_name
        self.args = args
        self.result = None
        self.error = None

    def __repr__(self):
        return (
            f"FunctionResult(FunctionName={self.function_name}, Result={self.result})"
        )

    def to_dict(self):
        return {
            "function_name": self.function_name,
            "args": self.args,
            "result": self.result,
            "error": self.error,
        }

    def clone(self):
        return copy.deepcopy(self)


class Subtask:
    def __init__(
        self, task_id, level, question, parent_ids, answer=None, function_results=None
    ):
        self.task_id: int = task_id
        self.level: int = level
        self.question: str = question
        self.parent_ids: list[int] = parent_ids
        self.answer: str = answer
        self.function_results = None
        self.need_tables: list[str] = None
        self.need_tools: list[str] = None

    def __repr__(self):
        return f"Subtask(ID={self.task_id}, Question={self.question}, ParentIDs={self.parent_ids})"

    def completed(self) -> bool:
        return self.answer is not None

    @classmethod
    def from_dict(cls, data):
        return cls(
            task_id=data["task_id"],
            level=data["level"],
            question=data["question"],
            parent_ids=data["parent_ids"],
            answer=data.get("answer"),
            function_results=data.get("function_results"),
        )

    def to_dict(self):
        """返回一个字典表示，用于数据存储或转换"""
        res = {
            "task_id": self.task_id,
            "level": self.level,
            "parent_ids": self.parent_ids,
            "question": self.question,
            "answer": self.answer,
            "need_tables": self.need_tables,
            "need_tools": self.need_tools,
            "function_results": self.function_results,
        }
        return res

    def to_simple_dict(self):
        """返回一个字典表示"""
        return {
            "task_id": self.task_id,
            "level": self.level,
            "parent_ids": self.parent_ids,
            "question": self.question,
            "answer": self.answer,
        }

    def to_update_dict(self):
        """返回一个字典表示，用于更新任务分解树"""
        return {
            "task_id": self.task_id,
            "level": self.level,
            "parent_ids": self.parent_ids,
            "question": self.question,
            "answer": self.answer,
        }

    def clone(self):
        return copy.deepcopy(self)


class Decomposition:
    def __init__(
        self,
        contains_time,
        format_requirement,
        assumption,
        subtasks,
        chain_of_subtasks,
        raw_question,
        dependency,
    ):
        self.contains_time: bool = contains_time
        self.raw_question: str = raw_question
        self.dependency: str = dependency
        self.format_requirement: str = format_requirement
        self.assumption: str = assumption
        self.subtasks: list[Subtask] = subtasks
        self.chain_of_subtasks: str = chain_of_subtasks
        self.need_tools: list[str] = None

    def __repr__(self):
        return (
            f"Decomposition(ContainsTime={self.contains_time}, FormatRequirement={self.format_requirement}, "
            f"Assumption={self.assumption}, Subtasks={self.subtasks})"
        )

    def get_task_by_id(self, task_id) -> Subtask:
        for subtask in self.subtasks:
            if subtask.task_id == task_id:
                return subtask
        return None

    @classmethod
    def from_dict(cls, data):
        subtasks = (
            [Subtask.from_dict(subtask) for subtask in data["subtasks"]]
            if "subtasks" in data
            else []
        )
        return cls(
            contains_time=data.get("contains_time", False),
            format_requirement=data.get("format_requirement", ""),
            assumption=data.get("assumption", ""),
            subtasks=subtasks,
            chain_of_subtasks=data.get("chain_of_subtasks", ""),
            raw_question=data.get("raw_question", ""),
            dependency=data.get("dependency", ""),
        )

    def to_dict(self):
        """返回一个字典表示，用于数据存储或转换"""
        return {
            "contains_time": self.contains_time,
            "format_requirement": self.format_requirement,
            "assumption": self.assumption,
            "raw_question": self.raw_question,
            "dependency": self.dependency,
            "chain_of_subtasks": self.chain_of_subtasks,
            "need_tools": self.need_tools,
            "subtasks": [subtask.to_dict() for subtask in self.subtasks],
        }

    def to_update_dict(self):
        """返回一个字典表示，用于更新任务分解树"""
        return {
            "contains_time": self.contains_time,
            "format_requirement": self.format_requirement,
            "assumption": self.assumption,
            "raw_question": self.raw_question,
            "dependency": self.dependency,
            "chain_of_subtasks": self.chain_of_subtasks,
            "subtasks": [subtask.to_update_dict() for subtask in self.subtasks],
        }

    def to_simple_dict(self):
        """返回一个字典表示"""
        return {
            "contains_time": self.contains_time,
            "format_requirement": self.format_requirement,
            "assumption": self.assumption,
            "raw_question": self.raw_question,
            "dependency": self.dependency,
            "chain_of_subtasks": self.chain_of_subtasks,
            "subtasks": [subtask.to_simple_dict() for subtask in self.subtasks],
        }

    def to_summary_dict(self):
        """返回一个字典表示"""
        return [subtask.to_simple_dict() for subtask in self.subtasks]

    def clone(self):
        return copy.deepcopy(self)

    def draw_table(self):
        """以表格形式打印任务分解"""
        from texttable import Texttable

        table = Texttable()
        table.set_deco(Texttable.HEADER)
        table.set_cols_align(["c", "c", "c", "c", "l", "l"])
        table.set_cols_width([5, 5, 10, 10, 68, 68])
        table.add_row(
            [
                "ID",
                "Level",
                "Parent IDs",
                "Completed",
                "Question",
                "Answer",
            ]
        )
        for task in self.subtasks:
            table.add_row(
                [
                    task.task_id,
                    task.level,
                    str(task.parent_ids),
                    task.completed(),
                    task.question,
                    task.answer,
                ]
            )
        logger.special(
            "\n",
            f"假设条件：{self.assumption}\n",
            f"格式要求：{self.format_requirement}\n",
            f"原始问题：{self.raw_question}\n",
            f"前后依赖：{self.dependency}",
            "\n",
            table.draw(),
        )


class ProblemSolution:
    def __init__(self, problem_id, question):
        self.id: str = problem_id
        self.question: str = question
        self.decomposition: Decomposition = None
        self.init_decomposition: Decomposition = None
        self.reasoning_answer: ReasoningAnswer = None
        self.error_message: str = None
        self.traceback: str = None

    def __repr__(self):
        return f"ProblemSolution(ID={self.id}, Question={self.question})"

    def to_dict(self):
        """返回一个字典表示，用于数据存储或转换"""
        res = {
            "id": self.id,
            "question": self.question,
            "decomposition": self.decomposition.to_dict(),
            "reasoning_answer": self.reasoning_answer.to_dict(),
        }
        return res

    def to_submit_json(self):
        """返回一个字典表示，用于提交"""
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.reasoning_answer.get_correct_answer(),
        }

    def to_summary_str(self):
        """返回一个字符串表示，用于问题总结"""
        return f"""
        原始问题：{self.question}
        格式要求：{self.decomposition.format_requirement}
        假设条件：{self.decomposition.assumption}
        任务链流程：{self.decomposition.chain_of_subtasks}
        任务前后依赖：{self.decomposition.dependency}
        解答过程：{self.decomposition.to_summary_dict()}
        """

    def to_correct_json(self):
        """返回一个字典表示，用于问题纠错"""
        return {
            "question": self.question,
            "reasoning": (
                self.reasoning_answer.reasoning if self.reasoning_answer else None
            ),
            "answer": self.reasoning_answer.answer if self.reasoning_answer else None,
        }

    def is_error(self) -> bool:
        return self.error_message is not None or self.traceback is not None

    def clone(self):
        return copy.deepcopy(self)


class VoteResult:
    def __init__(self, id, question, vote_times):
        self.id: str = id
        self.question: str = question
        self.init_question: str = question
        self.vote_times: int = vote_times
        self.solutions: list[ProblemSolution] = []
        self.final_answer: ReasoningAnswer = None
        self.reason: str = None

    def __repr__(self):
        return f"VoteResult(Solutions={self.solutions}, FinalAnswer={self.final_answer.get_correct_answer()})"

    def to_dict(self):
        """
        返回一个字典表示，用于数据存储或转换

        """
        return {
            "id": self.id,
            "question": self.question,
            "init_question": self.init_question,
            "vote_times": self.vote_times,
            "solutions": [solution.to_dict() for solution in self.solutions],
            "reason": self.reason,
            "final_reasoning_answer": self.final_answer.to_dict(),
        }

    def get_answers(self) -> list[str]:
        return [
            solution.reasoning_answer.get_correct_answer()
            for solution in self.solutions
        ]

    def clone(self):
        return copy.deepcopy(self)

    def to_submit_json(self):
        """返回一个字典表示，用于提交"""
        from utils import strtify

        return {
            "id": self.id,
            "question": self.init_question,
            "answer": strtify(self.final_answer.get_correct_answer()),
        }
