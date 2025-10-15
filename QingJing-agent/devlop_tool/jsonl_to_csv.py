# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import csv
import os

input_file = "questions/question.jsonl"
output_file = "tmp/output.csv"

os.makedirs("tmp", exist_ok=True)
with open(input_file, "r", encoding="utf-8") as infile, open(
    output_file, "w", encoding="utf-8", newline=""
) as outfile:
    writer = csv.writer(outfile)

    writer.writerow(["ID", "问题", "答案"])

    for idx, line in enumerate(infile, start=1):
        data = json.loads(line.strip())
        id = data.get("id", "")
        question = data.get("question", "")
        answer = data.get("answer", "")
        writer.writerow([id, question, answer])
