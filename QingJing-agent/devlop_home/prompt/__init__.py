# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

from .actor import ACTOR_PROMPT, REWRITE_PROMPT
from .critic import CORRECT_PROMPT
from .planner import PLANNER_PROMPT, UPDATE_PLAN_PROMPT
from .preflight import PREFLIGHT_TABLE_AND_TOOL_PROMPT, PREFLIGHT_TOOL_PROMPT
from .vote import VOTE_PROMPT
from .summary import SUMMARY_ONLY_ANSWER_PROMPT, SUMMARY_PROMPT

__all__ = [
    "ACTOR_PROMPT",
    "REWRITE_PROMPT",
    "CORRECT_PROMPT",
    "PLANNER_PROMPT",
    "UPDATE_PLAN_PROMPT",
    "PREFLIGHT_TABLE_AND_TOOL_PROMPT",
    "PREFLIGHT_TOOL_PROMPT",
    "VOTE_PROMPT",
    "SUMMARY_ONLY_ANSWER_PROMPT",
    "SUMMARY_PROMPT",
]
