# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json

input_file = "submits/2025-02-20-第1次-84.9.jsonl"
output_file = "submits/2025-02-20-第2次.jsonl"

def extract_answers(input_file, output_file):
    """
    读取 JSONL 文件，提取 '问题答案' 部分，并写入新的 JSONL 文件。

    :param input_file: 输入 JSONL 文件路径
    :param output_file: 输出 JSONL 文件路径
    """
    with open(input_file, "r", encoding="utf-8") as infile, open(
        output_file, "w", encoding="utf-8"
    ) as outfile:
        for line in infile:
            data = json.loads(line.strip())
            answer = data.get("answer", "")
            final_answer = answer.split("\n\n\n")[-1].strip()
            final_answer = final_answer.split("\n")[-1].strip()

            result = {
                "id": data.get("id"),
                "question": data.get("question"),
                "answer": final_answer,
            }

            outfile.write(json.dumps(result, ensure_ascii=False) + "\n")


extract_answers(input_file, output_file)
