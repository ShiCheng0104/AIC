# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
from pydantic import BaseModel
import logger

knowledge_file = "devlop_home/knowledge/knowledge.json"
table_meta_file = "devlop_home/knowledge/table_meta.json"


class Knowledge(BaseModel):
    @staticmethod
    def retrieve_knowledge(question: str, log: bool = True) -> list[str]:
        """
        根据问题检索背景知识

        :param question: 问题
        :param log: 是否打印日志
        :return: 背景知识列表
        """
        with open(knowledge_file, "r", encoding="utf-8") as file:
            knowledge_list = json.load(file)

        knowledge_set = set()

        for item in knowledge_list:
            for key in item["keys"]:
                add_flag = False
                if "&" in key:
                    sub_keys = key.split("&")
                    if all(sub_key.strip() in question for sub_key in sub_keys):
                        add_flag = True
                else:
                    add_flag = key in question
                if add_flag:
                    knowledge = item["knowledge"]
                    if item.get("example"):
                        knowledge += f"（示例：{item['example']}）"
                    knowledge_set.add(knowledge)
        if log:
            logger.debug(
                "【背景知识】\n"
                + "\n".join(
                    f"{idx + 1}. {line}" for idx, line in enumerate(list(knowledge_set))
                )
            )
        return list(knowledge_set)

    @staticmethod
    def get_tables_desc() -> str:
        """
        获得数据表描述字符串

        :return: 数据表描述字符串
        """
        with open(table_meta_file, "r", encoding="utf-8") as file:
            raw_table_data = json.load(file)

        table_data = [
            {"表名": item["table_name"], "表的描述信息": item["table_desc"]}
            for item in raw_table_data
        ]
        table_data_str = "\n".join(
            [
                f"{idx + 1}. 表名: {item['表名']}, 表的描述信息: {item['表的描述信息']}"
                for idx, item in enumerate(table_data)
            ]
        )
        return table_data_str

    @staticmethod
    def get_table_desc_by_names(table_names: list[str]) -> list[dict]:
        """
        根据数据表名获得数据表结构

        :param table_names: 数据表名列表
        :return: 数据表结构列表
        """
        with open(table_meta_file, "r", encoding="utf-8") as file:
            table_data = json.load(file)
        table_meta_list = [
            item for item in table_data if item["table_name"] in table_names
        ]
        return table_meta_list
