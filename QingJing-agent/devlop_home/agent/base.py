# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from pydantic import BaseModel, Field, model_validator

from llm import LLM
from schema import Memory, Message


class BaseAgent(BaseModel, ABC):
    """Agent的抽象基类

    子类必须实现`act`方法
    """

    name: str = Field(..., description="Agent的名称")
    description: Optional[str] = Field(None, description="Agent的描述")

    llm: LLM = Field(default_factory=LLM, description="LLM实例")
    memory: Memory = Field(default_factory=Memory, description="Agent的记忆模块")

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @abstractmethod
    def act(self, *args: Any, **kwargs: Any) -> Any:
        """
        定义 Agent 的行为逻辑。

        :param *args (Any): 不定位置参数，作为输入数据
        :param **kwargs (Any): 不定关键字参数，作为输入数据

        :return Any: Agent 的输出结果
        """
        pass

    @abstractmethod
    def get_knowledge(self, *args: Any, **kwargs: Any) -> str:
        """
        获取外部知识

        :param *args (Any): 不定位置参数，作为输入数据
        :param **kwargs (Any): 不定关键字参数，作为输入数据

        :return Any: 外部知识
        """

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
