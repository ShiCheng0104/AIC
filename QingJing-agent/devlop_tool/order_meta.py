# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import re

input_file = "meta.json"
output_file = "sorted_meta.json"


def natural_key(text):
    parts = re.split(r"(\d+)", text.lower())
    return [int(part) if part.isdigit() else part for part in parts]


def read_meta():
    with open(input_file, "r", encoding="utf-8") as f:
        return json.load(f)


def process_meta(meta):
    for table in meta:
        fields = table["字段名"]
        descs = table["字段含义"]

        field_descs = [
            {"字段名": fields[i], "字段含义": descs[i]} for i in range(len(fields))
        ]

        field_descs.sort(key=lambda x: natural_key(x["字段名"]))

        table["字段名"] = [item["字段名"] for item in field_descs]
        table["字段含义"] = [item["字段含义"] for item in field_descs]
    meta.sort(key=lambda x: natural_key(x["数据表名"]))


def write_meta(meta):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=4)


write_meta(process_meta(read_meta()))
