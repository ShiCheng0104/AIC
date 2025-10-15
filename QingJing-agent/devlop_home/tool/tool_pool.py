# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from typing import Any, Dict
from pydantic import BaseModel

from tool.base import ToolResult
from tool import (
    DataFilter,
    ToolCollection,
    BeforeOrLateRatioCalculator,
    DataAggregator,
    DeepseaOperationCounter,
    DurationCalculator,
    EnergyUsageCalculator,
    DeviceParamDetailQueryer,
    KeyActionRetriever,
    MathCalculator,
    PowerFuelCalculator,
    TimeConverter,
    TimeSorter,
    SalingStageQueryer,
)

all_available_tools = ToolCollection(
    BeforeOrLateRatioCalculator(),
    DataFilter(),
    DataAggregator(),
    DeepseaOperationCounter(),
    DeviceParamDetailQueryer(),
    DurationCalculator(),
    EnergyUsageCalculator(),
    KeyActionRetriever(),
    MathCalculator(),
    PowerFuelCalculator(),
    SalingStageQueryer(),
    TimeConverter(),
    TimeSorter(),
)

all_calculate_tools = ToolCollection(
    MathCalculator(),
    TimeConverter(),
    TimeSorter(),
)


class ToolPool(BaseModel):

    @staticmethod
    def get_all_tools() -> ToolCollection:
        return all_available_tools

    @staticmethod
    def execute(*, name: str, args: Dict[str, Any] = None) -> ToolResult:
        return ToolPool.get_all_tools().execute(name=name, tool_input=args)

    @staticmethod
    def get_calculate_tools() -> ToolCollection:
        return all_calculate_tools

    @staticmethod
    def get_tools_by_names(tool_names: list[str]) -> ToolCollection:
        return ToolCollection(
            *[item for item in all_available_tools.tools if item.name in tool_names]
        )
