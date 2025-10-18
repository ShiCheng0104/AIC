# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import os
import traceback
from schema import ApiConfig
import logger

config_file = "devlop_home/config.json"


class LLM:
    """LLM API类"""

    def __init__(self, config_name: str = "DEEPSEEK"):
        self.config_name = config_name
        self.api_config = LLM.load_api_config(config_name)

    @staticmethod
    def load_api_config(config_name: str = "DEEPSEEK") -> ApiConfig:
        """加载 API 配置"""
        with open(config_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        api_configs = [
            ApiConfig.from_dict(config) for config in data.get("api_configs", [])
        ]
        api_config = next(
            (config for config in api_configs if config.config_name == config_name),
            None,
        )
        return api_config

    @staticmethod
    def check_api_key(api_key_env: str) -> str:
        """
        检查API_KEY是否设定
        """
        if not api_key_env:
            return ""
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise RuntimeError(
                f"{api_key_env} is not set. Please set the environment variable."
            )
        return api_key

    @staticmethod
    def check_spark_base_url(base_url_env: str = "BASE_HOST") -> str:
        """
        检查SPARK的BASE_HOST
        """
        base_url = os.getenv(base_url_env)
        if not base_url:
            # logger.warning(
            #     f"{base_url_env} is not set. Please set the environment variable."
            # )
            return None
        else:
            return f"{base_url}/api/paas/v4/"

    def ask(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ):
        """
        获得对话结果

        :param messages: 对话消息
        :param tools: 工具
        :param model: 模型
        :return: 对话结果
        """
        model = self.api_config.model
        temperature = self.api_config.temperature
        stream = self.api_config.stream
        try:
            from openai import OpenAI

            if not self.api_config.base_url:
                raise RuntimeError("通用OpenAI接口配置 需要 base_url 参数")

            if self.api_config.type == "SPARK":
                base_url = LLM.check_spark_base_url() or self.api_config.base_url
            else:
                base_url = self.api_config.base_url

            client = OpenAI(
                base_url=base_url,
                api_key=LLM.check_api_key(self.api_config.api_key_env),
            )

            logger.trace("【请求回答】", str(messages), "【工具】", str(tools))

            create_kwargs = {
                "model": model,
                "stream": stream,
                "messages": messages,
                "temperature": temperature,
            }
            # DeepSeek 会在 tools=[] 时返回 400，只有在非空时才传参
            if tools:
                create_kwargs["tools"] = tools

            response = client.chat.completions.create(**create_kwargs)

            logger.trace("【回答结果】", str(response))

            if response.choices[0].finish_reason == "length":
                logger.warning("【回答长度过长】")

            return response
        except Exception as e:
            logger.error(f"【请求回答出错】: {e}\n{traceback.format_exc()}")
            raise e
