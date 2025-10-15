# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import os
import pandas as pd
from pathlib import Path

input_files = [
    # "submits/复赛A榜成绩/result_2025-03-19-第二次-52.4.jsonl",
    # "submits/复赛A榜成绩/result_2025-03-21-55.9.jsonl",
    "submits/复赛A榜成绩/result_2025-03-24-65.28.jsonl",
    "submits/复赛A榜成绩/result_2025-03-24-test.jsonl",
]
output_file = "devlop_output/compare.csv"


def read_jsonl(file):
    with open(file, "r", encoding="utf-8") as f:
        data = [json.loads(line.strip()) for line in f]
    df = pd.DataFrame(data, columns=["id", "question", "answer"])
    df.rename(
        columns={"id": "ID", "question": "问题", "answer": Path(file).name},
        inplace=True,
    )
    return df


def merge():
    dfs = [read_jsonl(file) for file in input_files]
    df_final = dfs[0][["ID", "问题"]].copy()
    for df in dfs:
        df_final = df_final.merge(df[["ID", df.columns[-1]]], on="ID", how="left")
    df_final = df_final.sort_values(by="ID").reset_index(drop=True)
    df_final.to_csv(output_file, index=False, encoding="utf-8")


merge()
