# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

"""Collection classes for managing multiple tools."""

from typing import Any, Dict, List

from tool.base import BaseTool, ToolException, ToolFailure, ToolResult


class ToolCollection:
    """A collection of defined tools."""

    def __init__(self, *tools: BaseTool):
        self.tools = tools
        self.tool_map = {}
        for tool in tools:
            self.tool_map[tool.name] = tool

    def __iter__(self):
        return iter(self.tools)

    def to_param(self) -> List[Dict[str, Any]]:
        return [tool.to_param() for tool in self.tools]

    def to_desc(self) -> str:
        desc_strs = [tool.to_desc_str() for tool in self.tools]
        return "\n".join(desc_strs)

    def names(self) -> List[str]:
        return [tool.name for tool in self.tools]

    def execute(self, *, name: str, tool_input: Dict[str, Any] = None) -> ToolResult:
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")
        try:
            result = tool(**tool_input)
            return result
        except ToolException as e:
            return ToolFailure(error=e.message)

    def get_tool(self, name: str) -> BaseTool:
        return self.tool_map.get(name)

    def add_tool(self, tool: BaseTool):
        self.tools += (tool,)
        self.tool_map[tool.name] = tool
        return self

    def add_tools(self, *tools: BaseTool):
        for tool in tools:
            self.add_tool(tool)
        return self
