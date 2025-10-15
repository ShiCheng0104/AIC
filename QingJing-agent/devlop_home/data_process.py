#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import pandas as pd
import numpy as np
from datetime import datetime
import json
import logger
import traceback

config_file = "devlop_home/config.json"

with open(config_file, "r", encoding="utf-8") as file:
    config = json.load(file)["data_config"]

table_name_map = config["file_mapping"]
data_path = config["input_data_path"]
output_path = config["output_data_path"]

os.makedirs(output_path, exist_ok=True)
logger.init()

key_action_field = "key_action"
no_key_action_flag = "False"
running_status_field = "running_status"
stage_field = "stage"
no_stage_flag = "False"
current_status_field = "current_status"
no_current_status_flag = "False"
running_flag = "开机运行中"
not_running_flag = "未运行"
sailing_stage_table_name = "航行状态表"


# In[ ]:


import time

program_start_time = time.time()
logger.info(
    "------------------------------【数据预处理开始】------------------------------"
)


# In[ ]:


# 合并数据
def cp_csv_files(input_path, out_path):
    for file_name in os.listdir(input_path):
        if file_name.endswith(".csv") and "字段释义" not in file_name:
            src = os.path.join(input_path, file_name)
            dst = os.path.join(out_path, file_name)

            df = pd.read_csv(src)

            if df.columns[0] == "Unnamed: 0":
                df.rename(columns={df.columns[0]: "index"}, inplace=True)

            if "csvTime" in df.columns:
                df = df.sort_values(by="csvTime").reset_index(drop=True)

            df.to_csv(dst, index=False)
            logger.info(f"已排序并复制文件 {src} -> {dst}")


cp_csv_files(data_path, output_path)


# In[ ]:


# 判定A架的开关机和有无电流
table_key = "Ajia_plc_1.csv"


def convert_to_numeric(value):
    """
    将值转换为数值类型，无法转换的返回 -1
    """
    try:
        return float(value)
    except ValueError:
        return -1


logger.special("开始判定A架开关机和有无电流")

df = pd.read_csv(os.path.join(output_path, table_key))
df["Ajia-3_v"] = df["Ajia-3_v"].apply(convert_to_numeric)
df["Ajia-5_v"] = df["Ajia-5_v"].apply(convert_to_numeric)
df[key_action_field] = no_key_action_flag
df[running_status_field] = not_running_flag
df[current_status_field] = no_current_status_flag
have_boot = -1
not_have_boot = -1

for i in range(1, df.shape[0]):
    prev_ajia3 = df.loc[i - 1, "Ajia-3_v"]
    prev_ajia5 = df.loc[i - 1, "Ajia-5_v"]
    curr_ajia3 = df.loc[i, "Ajia-3_v"]
    curr_ajia5 = df.loc[i, "Ajia-5_v"]

    # 停电条件：当前 Ajia-5_v == -1，且前一时刻 Ajia-5_v > 0 或 0
    # if curr_ajia5 == -1 and (prev_ajia5 >= 0):
    #     df.loc[i, key_action_field] = "停电"

    # A架开机条件：前一时刻 Ajia-3_v == -1，且当前 Ajia-3_v >= 0
    if prev_ajia3 == -1 and curr_ajia3 >= 0:
        df.loc[i, key_action_field] = "A架开机"
        have_boot = i
    if prev_ajia5 == -1 and curr_ajia5 >= 0:
        df.loc[i, key_action_field] = "A架开机"
        have_boot = i

    # A架关机条件：当前 Ajia-3_v == -1，且前一时刻 Ajia-3_v >= 0
    if curr_ajia3 == -1 and prev_ajia3 >= 0:
        df.loc[i, key_action_field] = "A架关机"
        not_have_boot = i
    if curr_ajia5 == -1 and prev_ajia5 >= 0:
        df.loc[i, key_action_field] = "A架关机"
        not_have_boot = i

    if have_boot != -1 and not_have_boot != -1 and have_boot < not_have_boot:
        for j in range(have_boot, not_have_boot + 1):
            df.loc[j, running_status_field] = running_flag
        have_boot = -1
        not_have_boot = -1

    # 有电流条件：前一时刻有一个或全部为0，下一刻均不为0
    if (prev_ajia3 <= 0 or prev_ajia5 <= 0) and (curr_ajia3 > 0 and curr_ajia5 > 0):
        df.loc[i, current_status_field] = "有电流"
    # 无电流条件：前一时刻均不为0，下一刻有一个或全部为0
    elif prev_ajia3 > 0 and prev_ajia5 > 0 and (curr_ajia3 <= 0 or curr_ajia5 <= 0):
        df.loc[i, current_status_field] = "无电流"

logger.success("A架开关机和有无电流判定完成")


# In[ ]:


# 处理A架角度数据

def find_next_target_value(index, current_target):
    """
    从指定索引开始查找下一个完美摆动目标值
    """
    for i in range(index, df.shape[0]):
        if current_target == 35:
            value = df.loc[i, "Ajia-0_v"]
            if value == "error":
                continue
            value = float(value)
            if value > 30 and value < 38:
                df.loc[i, "full_swing"] = True
                logger.debug("完美摆动：",df.loc[i, "csvTime"],"Ajia-0_v:", df.loc[i, "Ajia-0_v"])
                return i, -43
        elif current_target == -43:
            value = df.loc[i, "Ajia-0_v"]
            if value == "error":
                continue
            value = float(value)
            if value < -40 and value > -46:
                df.loc[i, "full_swing"] = True
                logger.debug("完美摆动：",df.loc[i, "csvTime"],"Ajia-0_v:", df.loc[i, "Ajia-0_v"])
                return i, 35
    return -1, -1

def detect_swings(df):
    """
    假设A架右舷同一方向上摆动超过10°即可算作一次摆动,标记摆动

    """
    index=0
    for i in range(0, df.shape[0]):
        value = df.loc[i, "Ajia-0_v"]
        if value == "error" or float(value) == 0:
            continue
        prev_value = float(value)
        index = i
        break
    
    curr_value = None
    for i in range(index+1, df.shape[0]):
        curr_value = df.loc[i, "Ajia-0_v"]
        if curr_value == "error":
            continue
        curr_value = float(curr_value)
        if prev_value*curr_value > 0 :
            if abs(curr_value-prev_value) > 10:
                df.loc[i, "directional_swing"] = True
                logger.debug("方向摆动超过10°：",df.loc[i, "csvTime"],"Ajia-0_v:", df.loc[i, "Ajia-0_v"])
                prev_value = curr_value
                continue
            elif abs(curr_value-prev_value) > 1.5 and prev_value< 30 and curr_value >30:
                prev_value = curr_value
                logger.debug("更新值为：",prev_value,"时间：",df.loc[i, "csvTime"])
                continue
        if prev_value*curr_value < 0:
            prev_value = curr_value
            continue
    logger.info("方向摆动超过10°处理完成")
        

logger.special("开始处理A架角度范围")

current_target = None
first_target_index = None
first_target = None
df["full_swing"] = False
df["directional_swing"] = False
for i in range(0, df.shape[0]):
    value = df.loc[i, "Ajia-0_v"]
    if value == "error":
        continue
    value = float(value)
    if value < -40 and value > -46:
        first_target_index = i
        first_target = -43
        current_target = 35
        break
    elif value > 30 and value < 38:
        first_target_index = i
        first_target = 35
        current_target = -43
        break
index1 = first_target_index + 1
while index1 < df.shape[0]:
    value = df.loc[index1, "Ajia-0_v"]
    if value == "error":
        continue
    value = float(value)
    index1, current_target = find_next_target_value(index1, current_target)
    if index1 == -1:
        break
    index1 += 1
logger.info("完美摆动处理完成")
detect_swings(df)
logger.success("A架角度范围处理完成")
# df = detect_swings(df)
# df.drop(columns=["Ajia-0_v_num"], inplace=True)
# print_surrounding_rows(df, "full_swing")
# print_surrounding_rows(df, "directional_swing")
# # df.to_csv(os.path.join(output_path, "test.csv"), index=False)
# logger.success("处理完成")


# In[ ]:


# 检查Ajia-0_v摆动至最小值和最大值
def check_ajia_0_v_extremes(df):
    flag = False
    extremes = [0] * len(df)
    for i in range(0, len(df)):
        if df.loc[i, "Ajia-0_v"] == "error":
            extremes[i] = 0
            continue
        curr_ajia_0_v = float(df.loc[i, "Ajia-0_v"])
        if -44 <= curr_ajia_0_v <= -42 and flag == True:
            flag = False
            extremes[i] = -1
        elif 34 <= curr_ajia_0_v <= 36 and flag == False:
            flag = True
            extremes[i] = 1
        else :
            extremes[i] = 0
    return extremes

# df["ajia_0_v_extremes"] = check_ajia_0_v_extremes(df)


# In[ ]:


# 根据开关机事件，将A架数据分为若干段
logger.special("根据开关机事件，将A架数据分为若干段")
start_time = None
segments = []

for index, row in df.iterrows():
    if row[key_action_field] == "A架开机":
        start_time = row["csvTime"]
    elif row[key_action_field] == "A架关机" and start_time is not None:
        end_time = row["csvTime"]
        segments.append((start_time, end_time))
        start_time = None
        
logger.success("共分为%d段" % len(segments))
for i, (start_time, end_time) in enumerate(segments):
    logger.info(f"第{i+1}段：{start_time} - {end_time}")


# In[ ]:


# 让LLM预测不好判断的动作

prompt_ajia_judge_file = "prompts/ajia_judge.md"

XIAFANG = """你是一个严谨且细心的数据分析助手，请根据给定的电流变化序列数据，准确返回符合规则的三个值。

规则要求：
1. 3个目标数值位于一段连续的非零数据中，该段应至少包含两次升降（即电流从约 56 上升至 80 以上）。  
2. 结果应满足以下条件：  
   - 第一个值：该段的第一个峰值，且一般大于 80。  
   - 第二个值：位于第一个和第三个值之间，由第一个峰值回落至小于60的第一个低值。  
   - 第三个值：重新达到峰值，且一般大于 80。 
3. 答案更可能位于峰值较多、非零数据段较长且满足上述要求的一段数据中
4. 忽略大于 200 的异常数据。  
5. 数据可能存在噪声，请谨慎判断。思考完成后，不需要返回思考过程，以列表形式返回三个值,回答中只有列表。
6. 若无法找到符合条件的三个值，请返回 [-100, -100, -100]，不要随意捏造。  

示例：
输入：
[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 56.6478, 56.5133, 60.8637, 56.3751, 56.3777, 56.3601, 61.1564, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 422.499, 56.2896, 66.3951, 60.8928, 57.7813, 56.3871, 66.3077, 62.5263, 56.3937, 58.0826, 90.0969, 87.5592, 83.9934, 56.5033, 59.3441, 58.0018, 56.3027, 56.2845, 56.3666, 101.763, 96.6118, 56.3492, 59.2629, 57.0112, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0]  
输出：  
[90.0969, 56.5033, 101.763]  

现有一组新的电流变化序列数据： 
<<L>>  
请根据上述规则，返回符合要求的三个值，答案仅包含列表格式。"""


HUISHOU = """你是一个严谨且细心的数据分析助手，请根据给定的电流变化序列数据，准确返回符合规则的三个值。

规则要求：
1. 数据列表应包含至少两段非零数据。  
2. 结果应满足以下条件：  
   - 第一个值：来自前一段非零数据的峰值，且一般大于 80。  
   - 第二个值：来自后一段非零数据的峰值，且一般应大于 80。  
   - 第三个值：位于第二个值之后，且一般小于 60，即从后一个峰值回落至低于 60 的第一个低值。  
3. 答案更可能位于非零数据段较长且满足上述要求的两段数据中
4. 忽略大于 200 的异常数据。  
5. 数据可能存在噪声，请谨慎判断。思考完成后，不需要返回思考过程，以列表形式返回三个值,回答中只有列表。  
6. 若无法找到符合条件的三个值，请返回 [-100, -100, -100]，不要随意捏造。  

示例：  
输入：  
[0.0, 0.0, 0.0, 0.0, 0.0, 57.0048, 56.8545, 61.9802, 56.8646, 56.8705, 56.777, 68.3751, 56.5526, 56.6556, 63.1736, 68.4542, 78.2151, 86.3214, 82.7017, 58.9111, 56.632, 56.9142, 56.6583, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 56.2542, 56.2177, 56.1263, 56.2697, 56.102, 59.5568, 57.5703, 57.6415, 56.9307, 57.0531, 56.9337, 58.582, 58.0159, 104.238, 96.6301, 97.1496, 56.5543, 63.426, 57.6552, 56.6086, 56.6611, 56.5601, 56.6476, 56.68, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0]  
输出：  
[86.3214, 104.238, 56.5543]  

现有一组新的电流变化序列数据：  
<<L>>  
请根据上述规则，返回符合要求的三个值，答案仅包含列表格式。"""


def limit_consecutive_zeros(lst, max_zeros=10):
    result = []
    zero_count = 0

    for num in lst:
        if num == 0:
            zero_count += 1
            if zero_count <= max_zeros:
                result.append(num)
        else:
            zero_count = 0
            result.append(num)

    return result


def predict_sequence_by_llm(L_sequence, is_xiafang: bool):
    from llm import LLM
    from utils import parse_res, load_api_config

    load_api_config("GLM")
    L_sequence = str(limit_consecutive_zeros(L_sequence))
    # with open(prompt_ajia_judge_file, "r", encoding="utf-8") as file:
    #     ajia_judge = file.read()

    if is_xiafang:
        ajia_judge = XIAFANG
    else:
        ajia_judge = HUISHOU

    prompt = ajia_judge.replace("<<L>>", L_sequence)
    messages = [{"role": "user", "content": prompt}]
    response = LLM().ask(messages)
    res = parse_res(response)
    logger.info("【LLM返回】：%s" % res)
    return res


def single_predict(L_sequence, is_xiafang: bool):
    result_list = json.loads(predict_sequence_by_llm(L_sequence, is_xiafang))
    if len(result_list) == 3:
        a = result_list[0]
        b = result_list[1]
        c = result_list[2]
        return a, b, c


def get_predict_result(L_sequence, is_xiafang: bool):
    try:
        return single_predict(L_sequence, is_xiafang)
    except Exception as e:
        logger.error("LLM预测失败，尝试再次预测：%s" % e)
        try:
            return single_predict(L_sequence, is_xiafang)
        except Exception as e:
            logger.error("LLM预测失败，返回默认值：%s" % e)
            return -100, -100, -100


# In[ ]:


# 判断A架关键动作的辅助函数
def extract_daily_power_on_times(df):
    """
    从CSV文件中提取一天内有两次开机的第一次和第二次开机时间。

    参数:
    file_path (str): CSV文件的路径，包含 'csvTime' 和 'status' 列。

    返回:
    first_start_times (list): 一天内有两次开机的第一次开机时间列表。
    second_start_times (list): 一天内有两次开机的第二次开机时间列表。
    """
    df["csvTime"] = pd.to_datetime(df["csvTime"])

    df["date"] = df["csvTime"].dt.date

    daily_segments = {}

    for date, group in df.groupby("date"):
        segments = []
        start_time = None

        for index, row in group.iterrows():
            if row[key_action_field] == "A架开机":
                start_time = row["csvTime"]
            elif row[key_action_field] == "A架关机" and start_time is not None:
                end_time = row["csvTime"]
                segments.append((start_time, end_time))
                start_time = None

        daily_segments[date] = segments

    daily_counts = {date: len(segments) for date, segments in daily_segments.items()}

    two_times_days = [date for date, count in daily_counts.items() if count == 2]

    first_start_times = []
    second_start_times = []

    for date in two_times_days:
        segments = daily_segments[date]
        first_start_times.append(segments[0][0])
        second_start_times.append(segments[1][0])

    return first_start_times, second_start_times


def find_peaks(input_data):
    """
    找到峰值

    :param input_data:输入序列
    :return: 峰值数量，峰值列表
    """
    data = [50 if 50 <= num <= 66 else num for num in input_data]

    # 找到峰值
    peaks = []
    for i in range(1, len(data) - 1):  # 从第二个元素遍历到倒数第二个元素
        if data[i] > data[i - 1] and data[i] > data[i + 1]:  # 判断是否为峰值
            peaks.append(data[i])  # 只记录峰值值
    peaks = [peak for peak in peaks if peak > 75]
    # 返回峰值格式和具体的峰值
    return len(peaks), peaks


def find_first_increasing_value(data):
    """
    找到列表中第一个从稳定值（66以下）开始增加的值

    :param data: 输入的数值列表
    :return: 第一个大于66的值。如果未找到，返回50
    """
    processed_data = [50 if 50 <= num <= 66 else num for num in data]

    for _, value in enumerate(processed_data):
        if value > 66 and value < 300:
            return value
    return 50

def find_qidiao_value(data): 
    tmp = data.copy()
    tmp = tmp.iloc[::-1].reset_index(drop=True)
    for i in range(len(tmp)):
        if tmp.iloc[i] < 75:
            return tmp[i]
    return tmp.iloc[-1]


def find_stable_value(data1, data2, peak1, peak2):
    """
    找到两个峰值之间的数据中，回落到稳定值的第一个值。
    假设稳定值在 50 到 60 之间。

    :param data1 (list): 数据列表
    :param data2 (list): 数据列表
    :param peak1 (float): 第一个峰值
    :param peak2 (float): 第二个峰值

    :return float or None: 稳定值，如果未找到则返回 None
    """
    try:
        start_index = data1.index(peak1)
        end_index = data1.index(peak2)
    except ValueError:
        return None

    between_peaks1 = data1[start_index : end_index + 1]
    between_peaks2 = data2[start_index : end_index + 1]

    for index, value in enumerate(between_peaks1):
        if 50 <= value <= 60 and 50 <= between_peaks2[index] <= 60:
            return value

    return None


def find_first_stable_after_peak(data, peak, stable_min=50, stable_max=60):
    """
    从峰值到列表末尾的数据中，找到第一个回落到稳定值的值。

    :param data (list): 数据列表
    :param peak (float): 峰值
    :param stable_min (float): 稳定值的最小值
    :param stable_max (float): 稳定值的最大值

    :return float or None: 稳定值，如果未找到则返回 None
    """
    try:
        start_index = data.index(peak)
    except ValueError:
        return None

    after_peak = data[start_index:]

    for value in after_peak:
        if stable_min <= value <= stable_max:
            return value

    return None


def extract_peak_pattern(current_presence_data):
    """
    从数据中提取峰值模式\n
    事件对：从有电流到无电流是一个

    :param current_presence_data: 有无电流数据
    :return: 返回时间段内各个事件对内的峰值数量
    """
    logger.info(f"【提取事件对】事件数量: {current_presence_data.shape[0]}")
    # print(current_presence_data)
    peak_pattern = []
    if current_presence_data.shape[0] >= 2 and current_presence_data.shape[0] % 2 == 0:
        for i in range(0, current_presence_data.shape[0], 2):
            event_start = current_presence_data.iloc[i]
            event_end = current_presence_data.iloc[i + 1]
            # 确保第一个事件是“有电流”，第二个事件是“无电流”
            if (
                event_start[current_status_field] == "有电流"
                and event_end[current_status_field] == "无电流"
            ):
                event_start_time = event_start["csvTime"]
                event_end_time = event_end["csvTime"]
                between_data = df[
                    (df["csvTime"] >= event_start_time)
                    & (df["csvTime"] <= event_end_time)
                ]
                ajia_5_data = list(between_data["Ajia-5_v"])
                logger.info(
                    f"【提取事件对】事件对 ({i}, {i + 1}) 之间的数据: {ajia_5_data}"
                )
                len_peaks, peak_L = find_peaks(ajia_5_data)
                logger.info(
                    f"【提取事件对】事件对 ({i}, {i + 1}) 之间的峰值数量: {len_peaks}，峰值为{peak_L}"
                )
                peak_pattern.append(len_peaks)
    return peak_pattern


# In[ ]:


# 判定A架的关键动作
# 提取每个区段内的“通电流”和“关电流”事件
from itertools import dropwhile

class PredictResult:
    def __init__(self, start_time, end_time):
        """
        预测结果类
        :param start_time: 起始时间
        :param end_time: 结束时间
        :param prediction: 预测结果
        """
        self.start_time = start_time
        self.end_time = end_time
        self.prediction: list[float] = None
        self.peak_pattern: list[int] = None

    def __str__(self):
        return f"预测时间段: {self.start_time} - {self.end_time}, 预测结果: {self.prediction}, 峰值模式: {self.peak_pattern}"

def is_deployment_complete_today(endtime: pd.Timestamp, pd_df: pd.DataFrame) -> bool:
    """
    判断当天从 00:00 到 endtime 之间的数据中，是否存在 'stage' 列的值为 '布放阶段结束' 的记录。

    参数：
    - endtime (pd.Timestamp): 结束时间，datetime 格式。
    - pd_df (pd.DataFrame): 包含 'csvTime' 和 'stage' 列的数据表。

    返回：
    - bool: 如果在当天 00:00 到 endtime 之间存在 '布放阶段结束' 记录，则返回 True，否则返回 False。
    """
    endtime = pd.to_datetime(endtime)
    pd_df['csvTime'] = pd.to_datetime(pd_df['csvTime'])
    # 获取当天 00:00 的时间
    start_time = endtime.normalize()  # 归一化到当天 00:00:00

    # 筛选当天 00:00 到 endtime 之间的数据
    mask = (pd_df['csvTime'] >= start_time) & (pd_df['csvTime'] <= endtime)
    filtered_df = pd_df[mask]

    # 判断 'stage' 列是否存在 '布放阶段结束'
    return '布放阶段结束' in filtered_df[stage_field].values

class Ajia_Result:
    def __init__(self, start_time, end_time):
        """
        预测结果类
        :param start_time: 起始时间
        :param end_time: 结束时间
        """
        self.start_time = start_time
        self.end_time = end_time
        self.event_pattern: list[int] = []
 
    def __str__(self):
        return f"时间段: {self.start_time} - {self.end_time}, 峰值模式: {self.event_pattern}"

LLM_predict_count = 0
LLM_predict_results: dict[int, tuple] = {}
df[stage_field]=no_stage_flag
peak_patterns =set()
Ajia_results = []
for segment in segments:
    start, end = segment
    ajia_result=Ajia_Result(start,end)
    logger.success(f"【开始处理时间段】开机时间: {start}, 关机时间: {end}")
    segment_data = df[(df["csvTime"] >= start) & (df["csvTime"] <= end)]
    logger.info(f"【处理时间段】区间数据：{list(segment_data['Ajia-5_v'])}")
    current_presence_data = df[
        (df["csvTime"] >= start)
        & (df["csvTime"] <= end)
        & (df[current_status_field].isin(["有电流", "无电流"]))
    ]
    ori_peak_pattern = extract_peak_pattern(current_presence_data)
    peak_pattern=list(dropwhile(lambda x: x == 0, ori_peak_pattern))
    current_presence_data=current_presence_data.iloc[2*(len(ori_peak_pattern)-len(peak_pattern)):]
    peak_patterns.add(tuple(peak_pattern))
    logger.info(f"【处理时间段】区间类型：{peak_pattern}")
    ajia_result.event_pattern=peak_pattern
    Ajia_results.append(ajia_result)
    deployment_complete_today = is_deployment_complete_today(start, df.copy())

    if (
        peak_pattern == [2]
        or peak_pattern == [3]
        or peak_pattern == [1, 3]
    ):
        # 下放阶段
        logger.info(f"【处理时间段】下放阶段")
        if peak_pattern == [2] or peak_pattern == [3]:
            event_start_time = current_presence_data.iloc[0]["csvTime"]
            event_end_time = current_presence_data.iloc[1]["csvTime"]
        elif peak_pattern == [1, 3]:
            event_start_time = current_presence_data.iloc[2]["csvTime"]
            event_end_time = current_presence_data.iloc[3]["csvTime"]
        between_data = df[
            (df["csvTime"] >= event_start_time) & (df["csvTime"] <= event_end_time)
        ]
        ajia_5_data = list(between_data["Ajia-5_v"])
        ajia_3_data = list(between_data["Ajia-3_v"])
        len_peaks, peak_L = find_peaks(ajia_5_data)
        
        # 缆绳解除：电流从高值回落至稳定值（50多），取50
        stable_value = find_stable_value(
            ajia_5_data, ajia_3_data, peak_L[len_peaks - 2], peak_L[len_peaks - 1]
        )
        indices = between_data.index[between_data["Ajia-5_v"] == stable_value].tolist()
        df.loc[indices, key_action_field] = "缆绳解除"
        # 征服者入水：缆绳解除的时间点往前推一分钟
        previous_indices = [idx - 1 for idx in indices if idx > 0]
        df.loc[previous_indices, key_action_field] = "征服者入水"
        # 征服者起吊：电流从稳定值（50多），取高于50的点
        first_peak_index = between_data.index[between_data["Ajia-5_v"] == peak_L[len_peaks - 2]].tolist()[0]
        first_increasing_value = find_qidiao_value(df.loc[(df["csvTime"] >= event_start_time) & (df.index <= first_peak_index), "Ajia-5_v"])
        indices = between_data.index[between_data["Ajia-5_v"] == first_increasing_value].tolist()[0]
        df.loc[indices+1, key_action_field] = "征服者起吊"
        # A架摆回：征服者入水后，电流重新增加到峰值（最大值点）
        indices = between_data.index[
            between_data["Ajia-5_v"] == peak_L[len_peaks - 1]
        ].tolist()
        df.loc[indices, key_action_field] = "A架摆回"
        df.loc[df["csvTime"] == start, stage_field] = "布放阶段开始"
        df.loc[df["csvTime"] == end, stage_field] = "布放阶段结束"
        df.loc[(df["csvTime"] > start) & (df["csvTime"] < end), stage_field] = "布放阶段中"
    elif (peak_pattern == [1, 2] or peak_pattern == [1, 1]):
        # 回收阶段
        logger.info(f"【处理时间段】回收阶段")
        # 第一个事件对
        event_start_time = current_presence_data.iloc[0]["csvTime"]
        event_end_time = current_presence_data.iloc[1]["csvTime"]
        between_data = df[
            (df["csvTime"] >= event_start_time) & (df["csvTime"] <= event_end_time)
        ]
        ajia_5_data = list(between_data["Ajia-5_v"])

        len_peaks, peak_L = find_peaks(ajia_5_data)
        # A架摆出：征服者起吊前，电流到达峰值（取峰值）
        indices = between_data.index[between_data["Ajia-5_v"] == peak_L[0]].tolist()
        df.loc[indices, key_action_field] = "A架摆出"
        # 第二个事件对
        event_start_time = current_presence_data.iloc[2]["csvTime"]
        event_end_time = current_presence_data.iloc[3]["csvTime"]
        between_data = df[
            (df["csvTime"] >= event_start_time) & (df["csvTime"] <= event_end_time)
        ]
        ajia_5_data = list(between_data["Ajia-5_v"])
        len_peaks, peak_L = find_peaks(ajia_5_data)
        max_value = max([x for x in ajia_5_data if x <= 200])

        # 征服者出水：电流峰值（取峰值）
        indices = between_data.index[between_data["Ajia-5_v"] == max_value].tolist()
        df.loc[indices, key_action_field] = "征服者出水"
        # 缆绳挂妥：征服者出水往前推一分钟
        previous_indices = [idx - 1 for idx in indices if idx > 0]
        df.loc[previous_indices, key_action_field] = "缆绳挂妥"
        # 征服者落座：电流从高值回落至稳定值（50多）（取50）
        first_stable_after_peak = find_first_stable_after_peak(ajia_5_data, max_value)
        indices = between_data.index[
            between_data["Ajia-5_v"] == first_stable_after_peak
        ].tolist()
        df.loc[indices, key_action_field] = "征服者落座"
        df.loc[df["csvTime"] == start, stage_field] = "回收阶段开始"
        df.loc[df["csvTime"] == end, stage_field] = "回收阶段结束"
        df.loc[(df["csvTime"] > start) & (df["csvTime"] < end), stage_field] = "回收阶段中"
    elif len(peak_pattern) > 0 and 1==0:
        LLM_predict_count += 1
        LLM_predict_results[LLM_predict_count] = PredictResult(start, end)
        logger.info("【处理时间段】交由大模型预测")
        segment_data=segment_data.copy()
        segment_data.loc[:, "csvTime"] = pd.to_datetime(segment_data["csvTime"])
        # 获取第一个值
        first_value = segment_data["csvTime"].iloc[0]
        #获取最后一个值
        last_value = segment_data["csvTime"].iloc[-1]
        # 判断小时是否大于12点
        is_hour_greater_than_12 = first_value.hour > 12
        is_hour_smaller_than_2= first_value.hour < 2
        is_lasttime_smaller_than_8 = last_value.hour < 8
        first_start_times, second_start_times = extract_daily_power_on_times(df=df)

        def predict(data, is_xiafang):
            data["predict_column"] = data.apply(
                lambda row: (
                    row["Ajia-3_v"]
                    if row["Ajia-5_v"] == 0 and row["Ajia-3_v"] > 0
                    else row["Ajia-5_v"]
                ),
                axis=1,
            )
            logger.info(
                "【处理时间段】----------------LLM预测的列表---------------------"
            )
            logger.info(str(list(segment_data["predict_column"])))
            try:
                a, b, c = get_predict_result(
                    list(segment_data["predict_column"]), is_xiafang
                )
            except Exception as e:
                logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")
                a, b, c = -100, -100, -100
            LLM_predict_results[LLM_predict_count].prediction = (a, b, c)
            LLM_predict_results[LLM_predict_count].peak_pattern = peak_pattern
            logger.success(
                "【处理时间段】LLM预测结果：",
                "下放阶段" if is_xiafang else "回收阶段",
                a,
                b,
                c,
            )
            if is_xiafang:
                indices = segment_data.index[
                    segment_data["predict_column"] == a
                ].tolist()
                df.loc[indices, key_action_field] = "征服者起吊"

                indices = segment_data.index[
                    segment_data["predict_column"] == b
                ].tolist()
                df.loc[indices, key_action_field] = "缆绳解除"
                previous_indices = [idx - 1 for idx in indices if idx > 0]
                df.loc[previous_indices, key_action_field] = "征服者入水"

                indices = segment_data.index[
                    segment_data["predict_column"] == c
                ].tolist()
                df.loc[indices, key_action_field] = "A架摆回"
                df.loc[df["csvTime"] == start, stage_field] = "布放阶段开始"
                df.loc[df["csvTime"] == end, stage_field] = "布放阶段结束"
                df.loc[(df["csvTime"] > start) & (df["csvTime"] < end), stage_field] = "布放阶段中"
            else:
                indices = segment_data.index[
                    segment_data["predict_column"] == a
                ].tolist()
                df.loc[indices, key_action_field] = "A架摆出"

                indices = segment_data.index[
                    segment_data["predict_column"] == b
                ].tolist()
                df.loc[indices, key_action_field] = "征服者出水"
                previous_indices = [idx - 1 for idx in indices if idx > 0]
                df.loc[previous_indices, key_action_field] = "缆绳挂妥"

                indices = segment_data.index[
                    segment_data["predict_column"] == c
                ].tolist()
                df.loc[indices, key_action_field] = "征服者落座"
                df.loc[df["csvTime"] == start, stage_field] = "回收阶段开始"
                df.loc[df["csvTime"] == end, stage_field] = "回收阶段结束"
                df.loc[(df["csvTime"] > start) & (df["csvTime"] < end), stage_field] = "回收阶段中"

        if (is_hour_greater_than_12 or (is_hour_smaller_than_2 and is_lasttime_smaller_than_8) or (first_value in second_start_times)):
            predict(segment_data, False)
        else:
            predict(segment_data, True)

    logger.success(f"【处理时间段完成】开机时间: {start}, 关机时间: {end}")
logger.trace('出现过的峰值模式：',peak_patterns) 


# In[ ]:


# print("LLM预测总数：", LLM_predict_count)
# for key, value in LLM_predict_results.items():
#     print(f"{key}: {value}")
# with open(f"{output_path}/LLM_predict_time_range.txt", "w") as f:
#     for key, value in LLM_predict_results.items():
#         f.write(f"{key}: {value}\n")


# In[ ]:


# 保存A架数据
logger.special("开始保存A架数据")
# df = df.drop(columns=["date"])
# df = df.drop(columns=['check_current_presence'])
with open("devlop_home/manual/stages.json", "r", encoding="utf-8") as f:
    manual_stage_data = json.load(f)
for item in manual_stage_data:
    begin_time=item['begin_time']
    end_time=item['end_time']
    stage=item['stage']
    df.loc[(df['csvTime'] > begin_time) & (df['csvTime'] < end_time),key_action_field] =no_key_action_flag
    if stage=='布放':
        df.loc[(df['csvTime'] == begin_time) , 'stage'] = '布放阶段开始'
        df.loc[(df['csvTime'] > begin_time) & (df['csvTime'] < end_time), 'stage'] = '布放阶段中'
        df.loc[(df['csvTime'] == end_time),'stage'] = '布放阶段结束'
    elif stage=='回收':
        df.loc[(df['csvTime'] == begin_time),'stage'] = '回收阶段开始'
        df.loc[(df['csvTime'] > begin_time) & (df['csvTime'] < end_time),'stage'] = '回收阶段中'
        df.loc[(df['csvTime'] == end_time),'stage'] = '回收阶段结束'
    else:
        df.loc[(df['csvTime'] >= begin_time) & (df['csvTime'] <= end_time),stage_field] =no_stage_flag
with open("devlop_home/manual/actions.json", "r", encoding="utf-8") as f:
    manual_keyaction_data = json.load(f)
for item in manual_keyaction_data:
    time=item['csvTime']
    column=item['values'][0]['name']
    value=item['values'][0]['value']
    df.loc[df['csvTime'] == time, column] = value
with open(f"{output_path}/ajia_event.txt", "w", encoding="utf-8") as f:
    for ajia_result in Ajia_results:
        f.write(f"{ajia_result}\n")
df.to_csv(os.path.join(output_path, table_key), index=False)
df.to_csv(os.path.join(output_path, table_name_map[table_key]), index=False)
logger.success("A架数据保存成功")


# In[ ]:


# 判定ON DP和OFF DP
table_key = "Port3_ksbg_9.csv"
logger.special("开始判定ON DP和OFF DP")
df = pd.read_csv(os.path.join(output_path, table_key))
df["P3_33"] = pd.to_numeric(df["P3_33"], errors="coerce")
df[key_action_field] = no_key_action_flag
df[running_status_field]= not_running_flag
have_boot = -1
not_have_boot = -1

for i in range(1, df.shape[0]):
    # ON DP
    if df.loc[i - 1, "P3_33"] == 0 and df.loc[i, "P3_33"] > 0:
        df.loc[i, key_action_field] = "ON DP"
        have_boot = i
    # OFF DP
    if df.loc[i - 1, "P3_33"] > 0 and df.loc[i, "P3_33"] == 0:
        df.loc[i, key_action_field] = "OFF DP"
        not_have_boot = i
    if have_boot != -1 and not_have_boot != -1 and have_boot < not_have_boot:
        for j in range(have_boot, not_have_boot):
            df.loc[j, running_status_field] = running_flag
        have_boot = -1
        not_have_boot = -1
        
df.to_csv(os.path.join(output_path, table_key), index=False)
df.to_csv(os.path.join(output_path, table_name_map[table_key]), index=False)
logger.success("ON DP和OFF DP数据保存成功")


# In[ ]:


# 处理发电机运行时长
logger.special("开始处理发电机运行时长")
dynamo_run_map = {
    f"No_1_{running_status_field}": ("Port1_ksbg_3.csv", "P1_88.14"),
    f"No_2_{running_status_field}": ("Port1_ksbg_4.csv", "P1_90.5"),
    f"No_3_{running_status_field}": ("Port2_ksbg_3.csv", "P2_73.8"),
    f"No_4_{running_status_field}": ("Port2_ksbg_3.csv", "P2_74.15"),
}


def mark_dynamo_run_status(data, field, run_status):
    data[run_status] = not_running_flag
    for i in range(0, data.shape[0]):
        if data.loc[i, field] == 1:
            data.loc[i, run_status] = running_flag
    return data


for run_status, (table_name, field) in dynamo_run_map.items():
    df = pd.read_csv(os.path.join(output_path, table_name))
    if field in df.columns:
        df = mark_dynamo_run_status(df, field, run_status)
        df.to_csv(os.path.join(output_path, table_name), index=False)
        logger.special(f"已处理 {table_name} 的 {field} 字段，标注 {run_status} 状态")


# In[ ]:


# 处理折臂吊车
from collections import Counter
table_key = "device_13_11_meter_1311.csv"

logger.special("开始判定折臂吊车关键动作")
df = pd.read_csv(os.path.join(output_path, table_key))
df["13-11-6_v"] = pd.to_numeric(df["13-11-6_v"], errors="coerce")
df[key_action_field] = no_key_action_flag
df[stage_field] = no_stage_flag

def sliding_window_5(arr):
    """滑动窗口大小为5的逻辑"""
    window_size = 5
    modified_arr = arr.copy()
    for i in range(len(arr) - window_size + 1):
        window = arr[i : i + window_size]
        if (
            window[1] < 10
            and window[2] < 10
            and window[3] < 10
            and window[0] >= 10
            and window[4] >= 10
        ):
            # 将 window[0] 包装成列表进行赋值
            modified_arr[i + 1 : i + 4] = [window[0]] * 3
    return modified_arr


def sliding_window_4(arr):
    """滑动窗口大小为4的逻辑"""
    window_size = 4
    modified_arr = arr.copy()
    for i in range(len(arr) - window_size + 1):
        window = arr[i : i + window_size]
        if window[1] < 10 and window[2] < 10 and window[0] >= 10 and window[3] >= 10:
            # 将 window[0] 包装成列表进行赋值
            modified_arr[i + 1 : i + 3] = [window[0]] * 2
    return modified_arr


def sliding_window_3(arr):
    """滑动窗口大小为3的逻辑"""
    window_size = 3
    modified_arr = arr.copy()
    for i in range(len(arr) - window_size + 1):
        window = arr[i : i + window_size]
        if window[1] < 10 and window[0] >= 10 and window[2] >= 10:
            # 直接赋值，因为只修改一个值
            modified_arr[i + 1] = window[0]
    return modified_arr


logger.info("【处理折臂吊车】开始应用滑动窗口逻辑")
df["13-11-6_v_new"] = sliding_window_5(df["13-11-6_v"].tolist())
df["13-11-6_v_new"] = sliding_window_4(df["13-11-6_v_new"].tolist())
df["13-11-6_v_new"] = sliding_window_3(df["13-11-6_v_new"].tolist())
logger.success("【处理折臂吊车】滑动窗口逻辑应用完成")

logger.info("【处理折臂吊车】开始判定折臂吊车的开机和关机事件")
df[running_status_field]= "未运行"
have_boot = -1
not_have_boot = -1
for i in range(1, df.shape[0]):
    # 开机
    if df.iloc[i - 1]["13-11-6_v"] == 0 and df.iloc[i]["13-11-6_v"] > 0:
        df.at[df.index[i], key_action_field] = "折臂吊车开机"
        have_boot = i
    # 关机
    if df.iloc[i - 1]["13-11-6_v"] > 0 and df.iloc[i]["13-11-6_v"] == 0:
        df.at[df.index[i], key_action_field] = "折臂吊车关机"
        not_have_boot = i
    if have_boot != -1 and not_have_boot != -1 and have_boot < not_have_boot:
        for j in range(have_boot, not_have_boot+1):
            df.loc[j, running_status_field] = running_flag
        have_boot = -1
        not_have_boot = -1
    # 检测由待机进入工作和由工作进入待机的事件
    if df.iloc[i - 1]["13-11-6_v_new"] < 10 and df.iloc[i]["13-11-6_v_new"] >= 10:
        df.at[df.index[i], stage_field] = "由待机进入工作"
    if df.iloc[i - 1]["13-11-6_v_new"] >= 10 and df.iloc[i]["13-11-6_v_new"] < 10:
        df.at[df.index[i], stage_field] = "由工作进入待机"
logger.success("【处理折臂吊车】折臂吊车的开机和关机事件判定完成")

logger.info("【处理折臂吊车】根据折臂吊车的开机和关机事件划分时间段")
segments = []
start_time = None
for index, row in df.iterrows():
    if row[key_action_field] == "折臂吊车开机":
        start_time = row["csvTime"]
    elif row[key_action_field] == "折臂吊车关机" and start_time is not None:
        end_time = row["csvTime"]
        segments.append((start_time, end_time))
        start_time = None
logger.success("【处理折臂吊车】时间段划分完成")

def find_most_frequent_number(lst):
    """
    使用 Counter 统计每个数的出现次数\n
    找到出现次数最多的数（如果有多个，只返回第一个）
    """
    counter = Counter(lst)
    most_common_number = counter.most_common(1)[0][0]
    return most_common_number
class Diaoche_Result:
    def __init__(self, start_time, end_time):
        """
        预测结果类
        :param start_time: 起始时间
        :param end_time: 结束时间
        """
        self.start_time = start_time
        self.end_time = end_time
        self.event_pattern: list[int] = []
 
    def __str__(self):
        return f"时间段: {self.start_time} - {self.end_time}, 事件模式: {self.event_pattern}"

diaoche_results = []
for segment in segments:
    start, end = segment
    logger.info(f"【开始处理时间段】开始时间：{start}，结束时间：{end}")
    diaoche_result=Diaoche_Result(start,end)
    actions_data = df[
        (df["csvTime"] >= start)
        & (df["csvTime"] <= end)
        & (df[stage_field].isin(["由待机进入工作", "由工作进入待机"]))
    ]
    segment_data = df[(df["csvTime"] >= start) & (df["csvTime"] <= end)]
    # 检查事件数量是否为偶数且等于6
    if actions_data.shape[0] > 0 and actions_data.iloc[0]["csvTime"] == start:
        actions_data = actions_data[2:]
        segment_data = segment_data[2:]
    if actions_data.shape[0] == 8:
        csv_time_as_datetime = pd.to_datetime(actions_data["csvTime"], errors="coerce")
        # 计算时间差
        time_diffs = (csv_time_as_datetime.iloc[1::2].values - csv_time_as_datetime.iloc[::2].values).astype("timedelta64[s]").astype(int)
        # 找到最小时间差的位置
        min_idx = time_diffs.argmin() * 2
        # 直接 drop 对应索引
        actions_data = actions_data.drop(actions_data.index[[min_idx, min_idx + 1]])
        
    logger.info(f"【处理时间段】事件数量: {actions_data.shape[0]}")
    diaoche_result.event_pattern = actions_data.shape[0]
    diaoche_results.append(diaoche_result)
    if actions_data.shape[0] == 6:
        # 处理每一对事件
        for i in range(0, 6, 2):
            event_start = actions_data.iloc[i]
            event_end = actions_data.iloc[i + 1]

            if (
                event_start[stage_field] == "由待机进入工作"
                and event_end[stage_field] == "由工作进入待机"
            ):
                event_start_time = event_start["csvTime"]
                event_end_time = event_end["csvTime"]
                between_data = df[
                    (df["csvTime"] >= event_start_time)
                    & (df["csvTime"] <= event_end_time)
                ]
                ajia_5_data = list(between_data["13-11-6_v"])

                # 找到最后一个大于9的值
                last_value_above_9 = next((x for x in reversed(ajia_5_data) if x > 9), None)

                if last_value_above_9 is not None:
                    all_indices = between_data.index[
                        between_data["13-11-6_v_new"] == last_value_above_9
                    ].tolist()
                    last_index = all_indices[-1] if all_indices else None

                    # 根据事件对的顺序更新status
                    if last_index is not None:
                        if i == 0:
                            df.loc[last_index, key_action_field] = "小艇检查完毕"
                        elif i == 2:
                            df.loc[last_index, key_action_field] = "小艇入水"
                        elif i == 4:
                            df.loc[last_index, key_action_field] = "小艇落座"
                else:
                    logger.info("列表中没有大于 9 的值")
    if actions_data.shape[0] == 4:
        # 处理每一对事件
        for i in range(0, 4, 2):
            event_start = actions_data.iloc[i]
            event_end = actions_data.iloc[i + 1]
            if (
                event_start[stage_field] == "由待机进入工作"
                and event_end[stage_field] == "由工作进入待机"
            ):
                event_start_time = event_start["csvTime"]
                event_end_time = event_end["csvTime"]
                between_data = df[
                    (df["csvTime"] >= event_start_time)
                    & (df["csvTime"] <= event_end_time)
                ]
                ajia_5_data = list(between_data["13-11-6_v"])

                # 找到最后一个大于9的值
                last_value_above_9 = next((x for x in reversed(ajia_5_data) if x > 9), None)

                if last_value_above_9 is not None:
                    all_indices = between_data.index[
                        between_data["13-11-6_v_new"] == last_value_above_9
                    ].tolist()
                    last_index = all_indices[-1] if all_indices else None

                    # 根据事件对的顺序更新status
                    if (
                        last_index is not None
                        and df.loc[last_index, key_action_field] == "False"
                    ):
                        if i == 0:
                            df.loc[last_index, key_action_field] = "小艇入水"
                        elif i == 2:
                            df.loc[last_index, key_action_field] = "小艇落座"
                else:
                    logger.warning("列表中没有大于 9 的值")
                # 保存结果
# df = df.drop(columns=[stage_field])
# df = df.drop(columns=['13-11-6_v_new'])
with open(f"{output_path}/diaoche_event.txt", "w", encoding="utf-8") as f:
    for diaoche_result in diaoche_results:
        f.write(f"{diaoche_result}\n")
df.to_csv(os.path.join(output_path, table_key), index=False)
df.to_csv(os.path.join(output_path, table_name_map[table_key]), index=False)
logger.success("【处理折臂吊车】保存数据完成")


# In[ ]:


# 判断标注4个巡航阶段
logger.special("开始标注航行状态")

output_filename = f"{sailing_stage_table_name}.csv"

file1 = "A架动作表.csv"
file2 = "艏侧推系统DP动作表.csv"
file3 = "Port3_ksbg_8.csv"
file4 = "Port4_ksbg_7.csv"
df_Ajia = pd.read_csv(os.path.join(output_path, file1), usecols=["csvTime", "stage"])
df_Dp = pd.read_csv(os.path.join(output_path, file2), usecols=["csvTime", "key_action"])
df_1tui = pd.read_csv(
    os.path.join(output_path, file3), usecols=["csvTime", "P3_15", "P3_32"]
)
df_2tui = pd.read_csv(
    os.path.join(output_path, file4), usecols=["csvTime", "P4_15", "P4_16"]
)
# 统一时间格式，并去除秒，只保留到分钟
for df in [df_Ajia, df_Dp, df_1tui, df_2tui]:
    df["csvTime"] = pd.to_datetime(df["csvTime"]).dt.strftime("%Y-%m-%d %H:%M")

# 以 df_1tui 为主，进行左连接合并
logger.special("开始标注动力定位状态")
df_merge = (
    df_1tui.merge(df_Ajia, on="csvTime", how="left")
    .merge(df_Dp, on="csvTime", how="left")
    .merge(df_2tui, on="csvTime", how="left")
)
df_merge["docking_status"] = "False"
df_merge["voyage_status"] = "False"
df_merge["escort_status"] = "False"
df_merge["dp_status"] = "False"
df_merge["dp_status"] = np.where(
    df_merge["key_action"] == "ON DP", "动力定位状态开始", "False"
)
df_merge["dp_status"] = np.where(
    df_merge["key_action"] == "OFF DP", "动力定位状态结束", df_merge["dp_status"]
)
dp_indexs=df_merge[df_merge["dp_status"].isin(["动力定位状态开始", "动力定位状态结束"])].index
i = 0
while i < len(dp_indexs) - 1:
    if df_merge.loc[dp_indexs[i], "dp_status"]=="动力定位状态结束" or df_merge.loc[dp_indexs[i+1], "dp_status"]=="动力定位状态开始":
        i+=1
        continue
    df_merge.loc[dp_indexs[i]+1:dp_indexs[i+1]-1, "dp_status"] = "动力定位状态中"
    i+=2

# 找到下一个P3_32为0的点
def find_next_zero(df, index):
    for i in range(index, len(df)):
        if df.loc[i, "P3_32"] == 0:
            return i
    return len(df)


# 找到下一个P3_32不为0的点
def find_next_nonzero(df, index):
    for i in range(index, len(df)):
        if df.loc[i, "P3_32"] > 300:
            return i
    return len(df)


logger.special("开始标注停泊状态")
df_merge["P3_32"] = pd.to_numeric(df_merge["P3_32"], errors="coerce")
first_index = 0
second_index = 0
for i in range(len(df)):
    if df_merge.loc[i, "P3_32"] == 0:
        first_index = i
        break
second_index = find_next_nonzero(df_merge, first_index + 1) - 1
df_merge.loc[first_index, "docking_status"] = "停泊状态开始"
df_merge.loc[second_index, "docking_status"] = "停泊状态结束"
df_merge.loc[first_index+1:second_index-1, "docking_status"] = "停泊状态中"
while 1:
    first_index = find_next_zero(df_merge, second_index + 1)
    if first_index == len(df_merge):
        break
    if first_index - second_index < 120:
        df_merge.loc[second_index, "docking_status"] = "False"
    else:
        df_merge.loc[first_index, "docking_status"] = "停泊状态开始"
    second_index = find_next_nonzero(df_merge, first_index + 1) - 1
    if second_index == len(df_merge) - 1:
        break
    df_merge.loc[second_index, "docking_status"] = "停泊状态结束"
    
stop_indexs=df_merge[df_merge["docking_status"].isin(["停泊状态开始", "停泊状态结束"])].index
i=0
while i < len(stop_indexs) - 1:
    if df_merge.loc[stop_indexs[i], "docking_status"]=="停泊状态结束" or df_merge.loc[stop_indexs[i+1], "docking_status"]=="停泊状态开始":
        i+=1
        continue
    df_merge.loc[stop_indexs[i]+1:stop_indexs[i+1]-1, "docking_status"] = "停泊状态中"
    i+=2
    


def label_sailing_begin_end(df):
    sailing_begin_index = -1
    sailing_end_index = 0
    flag = False
    for i in range(1, df.shape[0]):
        if df.loc[i, "stage"] == "布放阶段中" and df.loc[i, "key_action"] == "OFF DP" and df.loc[i, "docking_status"]=="False":
            df.loc[i, "escort_status"] = "伴航状态开始"
            flag = True
        if df.loc[i, "stage"] == "回收阶段中" and df.loc[i, "key_action"] == "ON DP" and df.loc[i, "docking_status"]=="False" and flag:
            flag = False
            df.loc[i - 1, "escort_status"] = "伴航状态结束"
        # if df.loc[i, "docking_status"]!="False" and sailing_begin_index > sailing_end_index:
        #     logger.info(f"航渡状态开始失效")
        #     sailing_end_index = i
        #     continue
        # if sailing_begin_index < sailing_end_index and df.loc[i, "P3_32"] >= 1000 and df.loc[i, "P3_15"] >= 200 and df.loc[i, "docking_status"]=="False":
        #     logger.info(f"找到航渡状态开始的时间：{df.loc[i, 'csvTime']}")
        #     sailing_begin_index = i
        #     continue
        # if sailing_begin_index > sailing_end_index and (df.loc[i, "P3_15"] < 128 or df.loc[i, "P3_32"] < 1000):
        #     sailing_end_index = i
        #     logger.info(f"找到航渡状态结束的时间：{df.loc[i, 'csvTime']}")
        #     df.loc[sailing_begin_index, "voyage_status"] = "航渡状态开始"
        #     df.loc[sailing_end_index, "voyage_status"] = "航渡状态结束"
        #     df.loc[sailing_begin_index+1:sailing_end_index-1, "voyage_status"] = "航渡状态中"
        if sailing_begin_index < sailing_end_index and df.loc[i, "P3_15"] >= 1000:
            sailing_begin_index = i
        if sailing_begin_index > sailing_end_index and df.loc[i, "P3_15"] < 1000:
            sailing_end_index = i
            df.loc[sailing_begin_index, "voyage_status"] = "航渡状态开始"
            df.loc[sailing_end_index, "voyage_status"] = "航渡状态结束"
            df.loc[sailing_begin_index+1:sailing_end_index-1, "voyage_status"] = "航渡状态中"
    escort_indexs=df_merge[df_merge["escort_status"].isin(["伴航状态开始", "伴航状态结束"])].index
    i=0
    while i < len(escort_indexs) - 1:
        if df_merge.loc[escort_indexs[i], "escort_status"]=="伴航状态结束" or df_merge.loc[escort_indexs[i+1], "escort_status"]=="伴航状态开始":
            i+=1
            continue
        df_merge.loc[escort_indexs[i]+1:escort_indexs[i+1]-1, "escort_status"] = "伴航状态中"    
        i+=2
        
    # hangdu_indexs=df_merge[df_merge["voyage_status"].isin(["航渡状态开始", "航渡状态结束"])].index
    # logger.info(f"航渡状态开始和结束的索引对应的时间：{df.loc[hangdu_indexs, 'csvTime']}")
    # last_end_index = 1
    # for i in range(0,len(hangdu_indexs)-1,2):
    #     flag=True
    #     if (
    #         not (df_merge.loc[hangdu_indexs[i]:hangdu_indexs[i+1]-1, "P3_15"] >= 128).all() 
    #         or (df_merge.loc[hangdu_indexs[i]:hangdu_indexs[i+1], "stage"].isin(["回收阶段中", "布放阶段中"]).any())
    #         or (df_merge.loc[hangdu_indexs[i]:hangdu_indexs[i+1], "escort_status"].isin(["伴航状态中"]).any())
    #         or (df_merge.loc[hangdu_indexs[i]:hangdu_indexs[i+1], "P3_15"] > 1000).sum() < 10  # 计算区间内大于 1000 的数据量
    #     ):
    #         df_merge.loc[hangdu_indexs[i]:hangdu_indexs[i+1], "voyage_status"] = "False"
    #         flag=False
    #     if flag and hangdu_indexs[i]-last_end_index<10 and i>0 and df_merge.loc[last_end_index,"voyage_status"]!="False":
    #         df_merge.loc[last_end_index:hangdu_indexs[i], "voyage_status"] = "航渡状态中"
    #     last_end_index=hangdu_indexs[i+1]
    # hangdu_indexs=df_merge[df_merge["voyage_status"].isin(["航渡状态开始", "航渡状态结束"])].index
    # for i in range(0,len(hangdu_indexs)-1,2):
    #     if hangdu_indexs[i+1]-hangdu_indexs[i]<15:
    #         df_merge.loc[hangdu_indexs[i]:hangdu_indexs[i+1], "voyage_status"] = "False"
            


logger.special("开始标注航渡状态和伴航状态")
label_sailing_begin_end(df_merge)
df_merge.to_csv(os.path.join(output_path, output_filename), index=False)
logger.special("航行状态标注完毕")


# In[ ]:


logger.special("开始标注放缆收缆")
df=pd.read_csv(os.path.join(output_path, 'Jiaoche_plc_1.csv'))
df["deploy_retrieve_status"] = 'false'
index=0
for i in range(1, df.shape[0]):
    prev_value = df.loc[i-1, "PLC_point0_value"]
    curr_value = df.loc[i, "PLC_point0_value"]
    if prev_value == "error" or curr_value == "error":
        continue
    prev_value = float(prev_value)
    curr_value = float(curr_value)
    if (curr_value-prev_value) > 5:
        df.loc[i, "deploy_retrieve_status"] = '放缆'
        logger.debug("放缆一次：",df.loc[i, "csvTime"],"原长度:", prev_value, "当前长度:", curr_value)
        continue
    elif (prev_value-curr_value) > 5:
        df.loc[i, "deploy_retrieve_status"] = '收缆'
        logger.debug("收缆一次：",df.loc[i, "csvTime"],"原长度:", prev_value, "当前长度:", curr_value)
        continue
df.to_csv(os.path.join(output_path, 'Jiaoche_plc_1.csv'), index=False)
logger.special("放缆收缆标注完毕")
    
        


# In[ ]:


import time
program_end_time = time.time()
elapsed_time_minutes = (program_end_time - program_start_time) / 60
logger.debug(f"【数据预处理运行时间】 {elapsed_time_minutes:.2f} 分钟")
logger.info(
    "------------------------------【数据预处理结束】------------------------------"
)

