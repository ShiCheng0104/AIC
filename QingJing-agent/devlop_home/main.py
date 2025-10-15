# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import json
import concurrent.futures as cf
import os
import sys
import traceback
import time
from schema import VoteResult
import logger
import utils
from agent.start import process_one
from flask_socketio import SocketIO

result_dir = "devlop_output/results"
solution_dir = "devlop_output/solutions"
answer_filepath = "devlop_home/test.jsonl"


def load_params():
    """
    加载参数
    """
    utils.load_api_config()
    utils.load_module_config()

    in_param_path = sys.argv[1]

    with open(in_param_path, "r", encoding="utf-8") as load_f:
        content = load_f.read()
        input_params = json.loads(content)

    question_filepath = None
    source_data_filepath = None

    try:
        question_filepath = input_params["fileData"]["questionFilePath"]
        source_data_filepath = input_params["fileData"]["sourceDataFilePath"]
    except Exception as e:
        logger.error(f"【读取输入参数出错】{input_params}")

    date_str = time.strftime("%Y-%m-%d", time.localtime())
    if len(sys.argv) > 2:
        out_path = sys.argv[2]
    else:
        out_path = os.path.join(result_dir, f"result_{date_str}.jsonl")
    solution_path = os.path.join(solution_dir, f"solution_{date_str}.json")

    os.makedirs(result_dir, exist_ok=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    os.makedirs(os.path.dirname(solution_path), exist_ok=True)

    return question_filepath, source_data_filepath, solution_path, out_path

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许所有域名访问
socketio = SocketIO(app, cors_allowed_origins="*",logger=True,engineio_logger=True)
logger.init_logger_with_flask(socketio)

def run(test_question,socketio):
    vote_res = process_one({'answer': '', 'id': "测试问题", 'question': test_question},socketio)
    return vote_res.final_answer.answer


@app.route('/process', methods=['POST'])
def process_message():
    data = request.get_json()
    input_message = data['message']
    result = run(input_message,socketio)
    return jsonify({'result': result})

def main():
    vote_result_list = []
    submit_result_list = []
    question_filepath, source_data_filepath, solution_path, out_path = load_params()

    with open(question_filepath, "r", encoding="utf-8") as f:
        question_list = [json.loads(line.strip()) for line in f]

    socketio.run(app,host='0.0.0.0', port=5000, debug=True,allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    logger.init()
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
