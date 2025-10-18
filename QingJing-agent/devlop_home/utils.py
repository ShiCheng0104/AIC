# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

"""工具函数"""

import json
import numpy as np
import pandas as pd
import logger
import traceback
from schema import ApiConfig, ModuleConfig
from texttable import Texttable

config_file = "devlop_home/config.json"
font_file = "devlop_home/msyh.ttf"

api_config = None
module_config = None


def load_api_config(config_name: str = "DEEPSEEK") -> ApiConfig:
    """加载 API 配置"""
    global api_config
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


def load_module_config() -> ModuleConfig:
    """加载模块配置"""
    global module_config
    with open(config_file, "r", encoding="utf-8") as file:
        data = json.load(file)
    module_config = ModuleConfig.from_dict(data["module_config"])
    return module_config


def strtify(obj):
    """
    将对象转换为字符串
    """
    if isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False)
    return str(obj)


def parse_res(response):
    """
    解析结果
    """
    try:
        res = response.choices[0].message.content
        if "</think>" in res:
            res = res.split("</think>", 1)[1]
        if "```json" in res and "```" in res:
            res = res.split("```json", 1)[1]
            res = res.split("```", 1)[0]
        res = res.strip().replace("\n", "")
        return res
    except Exception as e:
        logger.trace(f"【解析结果出错】: {e}", traceback.format_exc())
        return res


def custom_serializer(obj):
    import pandas as pd

    if isinstance(obj, np.int64):
        return int(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.to_pydatetime()
    # raise TypeError(f"Type {obj.__class__.__name__} not serializable")
    return str(obj)


def try_run(func, *args, max_retries=3, **kwargs):
    attempts = 0
    while attempts < max_retries:
        res = func(*args, **kwargs)
        if not res:
            attempts += 1
            logger.error(
                f"第 {attempts} 次执行 {func.__name__} 出错，\n{traceback.format_exc()}"
            )
        else:
            return res
    logger.error(f"执行 {func.__name__} 失败，已达到最大重试次数 {max_retries} 次。")


def parse_code(response):
    """
    解析代码
    """
    try:
        res = response.choices[0].message.content
        if "```" in res:
            res = res.split("```python", 1)[1]
            res = res.split("```", 1)[0]
        res = res.strip()
        return res
    except Exception:
        return res


def save_submit_result(submit_result_list, submit_path: str):
    """
    保存提交结果
    """
    submit_result_list.sort(key=lambda x: x["id"])
    with open(submit_path, "w", encoding="utf-8") as f:
        for result in submit_result_list:
            f.write(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    default=custom_serializer,
                )
                + "\n"
            )


def save_solutions(vote_results, result_path: str):
    """
    保存解答过程
    """
    vote_results.sort(key=lambda x: x.id)
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(
            json.dumps(
                [vote_res.to_dict() for vote_res in vote_results],
                ensure_ascii=False,
                default=custom_serializer,
            )
        )


def get_table_meta(table_meta_filepath, table_name, columns):
    """
    根据数据表名和列名，获取数据表中指定列的元信息。

    :param table_name (str): 数据表名
    :param columns (list): 需要查询的列名列表

    :return dict: 包含列名和对应元信息的字典，或错误信息
    """

    with open(table_meta_filepath, "r", encoding="utf-8") as file:
        raw_table_data = json.load(file)

    table_meta = None

    for table in raw_table_data:
        if table["table_name"] == table_name:
            table_meta = table

    if table_meta is None:
        return {
            "error": f"数据表 {table_name} 的元信息不存在",
        }

    column_desc = {}
    for column in columns:
        for tmp in table_meta["columns"]:
            if tmp["name"] == column:
                column_desc[column] = tmp["desc"]

    return column_desc


def render_text_table(result: dict) -> str:
    """
    渲染数据表格

    :param result (dict): 数据字典

    :return str: 返回数据表格
    """
    if not result:
        return

    table = Texttable()
    table.set_deco(Texttable.HEADER)

    column_widths = [
        10 if header not in ["csvTime", "current_status"] else 20
        for header in result.keys()
    ]
    table.set_cols_width(column_widths)

    table.set_cols_align(["c" for _ in result.keys()])

    headers = list(result.keys())
    table.add_row(headers)

    rows = zip(*[result[col] for col in headers])
    for row in rows:
        table.add_row(row)

    return table.draw()


def load_and_filter_data(
    file_path, start_time, end_time, power_column
) -> tuple[pd.DataFrame | str]:
    """
    加载 CSV 文件并筛选指定时间范围内的数据

    :param file_path (str): CSV 文件路径
    :param start_time (str): 开始时间
    :param end_time (str): 结束时间
    :param power_column (str): 功率列名

    :return DataFrame|str: 筛选后的 DataFrame | 错误
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return f"文件 {file_path} 未找到"
    try:
        df["csvTime"] = pd.to_datetime(df["csvTime"])
    except Exception as e:
        return f"时间列转换失败: {e}"

    if isinstance(start_time, str):
        start_time_dt = pd.to_datetime(start_time)
    if isinstance(end_time, str):
        end_time_dt = pd.to_datetime(end_time)

    filtered_data = df[
        (df["csvTime"] >= start_time_dt) & (df["csvTime"] <= end_time_dt)
    ].copy()

    if filtered_data.empty:
        return "筛选数据为空"

    filtered_data.loc[:, "diff_seconds"] = (
        filtered_data["csvTime"].diff().dt.total_seconds().shift(-1)
    )

    # filtered_data.loc[filtered_data.index[-1], "diff_seconds"] = (
    #     (end_time_dt - pd.to_datetime(filtered_data.iloc[-1]["csvTime"])).total_seconds()
    # )

    filtered_data.loc[:, "energy_kWh"] = (
        filtered_data["diff_seconds"] * filtered_data[power_column] / 3600
    )

    return filtered_data
