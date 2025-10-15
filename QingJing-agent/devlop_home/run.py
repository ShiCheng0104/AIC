# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import concurrent.futures as cf
import os
import time
import argparse
from schema import VoteResult
import logger
import utils
from agent.start import process_one

submit_dir = "devlop_output/results"
solution_dir = "devlop_output/solutions"

test_input_path = "devlop_data/questions/test.jsonl"
production_input_path = "devlop_data/questions/rematch_A.jsonl"


def parse_args():
    parser = argparse.ArgumentParser(description="以测试或生产模式运行脚本。")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-t", "--test", action="store_true", help="以测试模式运行")
    group.add_argument("-p", "--production", action="store_true", help="以生产模式运行")
    parser.add_argument(
        "-s",
        "--splice_index",
        action="store_true",
        help="仅处理问题文件中的第一个问题，用于测试",
    )
    parser.add_argument("-q", "--question_file", type=str, help="指定问题文件")
    parser.add_argument(
        "-c",
        "--api_config_name",
        type=str,
        default="GLM",
        help="API 配置名称，默认为 GLM",
    )
    args = parser.parse_args()

    if not args.test and not args.production:
        parser.error("必须指定 -t（测试模式）或 -p（生产模式）之一。")

    if not utils.load_api_config(args.api_config_name):
        parser.error(f"未找到名称为 {args.api_config_name} 的 API 配置。")

    return args


def init():
    """
    初始化
    """
    logger.init()
    utils.load_module_config()
    os.makedirs(submit_dir, exist_ok=True)
    os.makedirs(solution_dir, exist_ok=True)


def main():
    init()
    args = parse_args()
    is_test = args.test
    question_path = args.question_file or (
        test_input_path if is_test else production_input_path
    )
    splice_index = args.splice_index
    max_workers_main = utils.module_config.max_workers_main
    max_workers_subtask = utils.module_config.max_workers_subtask

    with open(question_path, "r", encoding="utf-8") as f:
        question_list = [json.loads(line.strip()) for line in f]
    if splice_index:
        question_list = question_list[:1]

    logger.debug(
        f"【运行模式】: {'测试' if is_test else '生产'},",
        f"【问题总数】: {len(question_list)},",
        f"【投票次数】: {utils.module_config.vote_times},",
        f"【问题并发线程数】: {max_workers_main},",
        f"【子任务并发线程数】: {max_workers_subtask},",
        f"【仅处理第一个问题】: {splice_index},",
        f"【问题文件】: {question_path}",
    )

    date_str = time.strftime("%Y-%m-%d", time.localtime())
    submit_path = os.path.join(submit_dir, f"试试又不会怎样_result_{date_str}.jsonl")
    solution_path = os.path.join(solution_dir, f"solution_{date_str}.json")

    vote_results = []
    submit_result_list = []

    with cf.ThreadPoolExecutor(max_workers=max_workers_main) as executor:
        future_list = [executor.submit(process_one, item) for item in question_list]
        for future in cf.as_completed(future_list):
            vote_res = future.result()
            if isinstance(vote_res, VoteResult):
                vote_results.append(vote_res)
                submit_result_list.append(
                    vote_res.to_submit_json()
                    if isinstance(vote_res, VoteResult)
                    else vote_res
                )
                utils.save_submit_result(submit_result_list, submit_path)
                utils.save_solutions(vote_results, solution_path)
            else:
                submit_result_list.append(vote_res)
                utils.save_submit_result(submit_result_list, submit_path)


if __name__ == "__main__":
    start_time = time.time()
    logger.info(
        "------------------------------【程序开始】------------------------------"
    )
    main()
    end_time = time.time()
    elapsed_time_minutes = (end_time - start_time) / 60
    logger.debug(f"【程序运行时间】 {elapsed_time_minutes:.2f} 分钟")
    logger.info(
        "------------------------------【程序结束】------------------------------"
    )
