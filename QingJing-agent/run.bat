jupyter nbconvert --to script devlop_home/data_process.ipynb
python devlop_home/data_process.py
python devlop_home/main.py .\devlop_data\input_param.json .\devlop_result\answer.jsonl
pause