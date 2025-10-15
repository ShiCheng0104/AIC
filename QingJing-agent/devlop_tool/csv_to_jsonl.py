# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import csv
import os

input_file = "submits/A榜问题答案.csv"
output_file = "tmp/output.jsonl"

os.makedirs("tmp", exist_ok=True)

with open(input_file, "r", encoding="utf-8") as infile, open(
    output_file, "w", encoding="utf-8", newline=""
) as outfile:
    reader = csv.reader(infile)
    next(reader)
    for row in reader:
        id, question, answer = row
        data = {
            "id": id,
            "question": question,
            "answer": answer,
        }
        outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
