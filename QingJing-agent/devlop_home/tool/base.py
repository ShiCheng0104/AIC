# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from abc import ABC, abstractmethod
import inspect
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    params: Dict = Field(default_factory=dict)
    output: Dict = Field(default_factory=dict)
    error: Optional[str] = Field(default=None)

    def __str__(self):
        return str(self.to_dict())

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        return type(self)(**{**self.model_dump(), **kwargs})

    def to_dict(self):
        if self.error:
            return {"error": self.error}
        else:
            return {"output": self.output}


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""

    def to_dict(self):
        return {"error": self.error}


class ToolException(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message


class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None
    input: str
    output: str
    examples: Optional[List[str]] = []
    notices: Optional[List[str]] = []

    table_meta_filepath: str = "devlop_home/knowledge/table_meta.json"
    table_base_path: str = "devlop_home/data"

    def __call__(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        return self.execute(**kwargs)

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_desc_str(self) -> str:
        desc_str = f"函数名称：{self.name}，输入：{self.input}，输出：{self.output}"
        if len(self.notices) > 0:
            desc_str += f"，【注意】：{self.notices}"
        if len(self.examples) > 0:
            desc_str += f"，【示例问题】：{self.examples}"
        return desc_str

    def get_params(self) -> Dict:
        params = {}
        for k in {
            k: v for k, v in inspect.signature(self.execute).parameters.items()
        }.keys():
            params[k] = dict(locals())[k]
        return params
